"""Factor-engine behaviour tested through the primary seam:
seed synthetic vintaged observations into SQLite, run the pipeline,
assert on states, contributions, and rendered output.
"""

import datetime

import pytest

from macro_packet.engine import compute_state, factor_states, indicator_readings, render_state
from macro_packet.specs import INDICATORS
from macro_packet.store import Observation, Store

AS_OF = "2026-08-25"
WEEKS = 56  # weekly span 2025-08 .. 2026-08 so the last release is fresh at AS_OF


def _weekly(series, start, weeks, value_fn, release_lag_days=4):
    obs = []
    for i in range(weeks):
        period = start + datetime.timedelta(days=7 * i)
        release = period + datetime.timedelta(days=release_lag_days)
        obs.append(Observation(series, period.isoformat(), value_fn(i), release.isoformat()))
    return obs


def _monthly(series, months, value_fn, start=datetime.date(2025, 7, 1), release_day=6):
    """Monthly observations; default span 2025-07..2026-08 stays fresh at AS_OF."""
    obs = []
    for i in range(months):
        y, m = divmod(start.month - 1 + i, 12)
        period = datetime.date(start.year + y, m + 1, min(start.day, 28))
        obs.append(Observation(
            series, period.isoformat(), value_fn(i),
            period.replace(day=min(release_day, 28)).isoformat(),
        ))
    return obs


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "engine.db")
    # Growth: benign claims, steadily rising payrolls, steady unemployment
    s.ingest(_weekly("ICSA", datetime.date(2025, 8, 1), WEEKS, lambda i: 220_000))
    s.ingest(_monthly("PAYEMS", 14, lambda i: 150_000 + 20 * i))
    s.ingest(_monthly("UNRATE", 14, lambda i: 4.2))
    return s


def test_polarity_rising_claims_lowers_growth(tmp_path):
    s = Store(tmp_path / "polarity.db")
    s.ingest(_weekly("ICSA", datetime.date(2025, 8, 1), WEEKS,
                     lambda i: 300_000 if i == WEEKS - 1 else 220_000))
    spec, z = indicator_readings(s, INDICATORS, AS_OF)["ICSA"]
    assert spec.polarity == -1
    assert z < 0  # claims spiked above their window -> negative Growth reading


def test_polarity_rising_yields_raise_rates_pressure():
    s = Store(":memory:")
    # daily-ish yields: flat at 3.5, jump to 4.5 at the boundary
    s.ingest(_weekly("DGS2", datetime.date(2025, 8, 1), WEEKS,
                     lambda i: 4.5 if i == WEEKS - 1 else 3.5))
    _, z = indicator_readings(s, INDICATORS, AS_OF)["DGS2"]
    assert z > 0  # yield jumped above its window -> positive Rates Pressure


def test_contributions_sum_to_factor_state(store):
    states = factor_states(store, AS_OF)
    # auditable down to inputs: each factor's state equals the sum of its
    # renormalized clamped-z contributions
    readings = indicator_readings(store, INDICATORS, AS_OF)
    by_factor = {}
    for spec, z in readings.values():
        by_factor.setdefault(spec.factor, []).append((spec.weight, z))
    for factor, members in by_factor.items():
        wsum = sum(w for w, _ in members)
        expected = round(sum(w / wsum * max(-3.0, min(3.0, z)) for w, z in members), 6)
        assert abs(states[factor].state - expected) < 1e-6
    assert set(by_factor) == {"G"}  # only Growth was seeded


def test_missing_indicator_renormalizes_with_visible_confidence(tmp_path):
    s = Store(tmp_path / "missing.db")
    s.ingest(_monthly("PAYEMS", 14, lambda i: 150_000))
    s.ingest(_monthly("UNRATE", 14, lambda i: 4.2))
    # ICSA absent entirely
    g = factor_states(s, AS_OF)["G"]
    assert g.missing == ("ICSA",)
    assert g.confidence == pytest.approx(0.60)  # (0.35 + 0.25) / 1.00
    # contributions still sum to state despite renormalization
    readings = indicator_readings(s, INDICATORS, AS_OF)
    members = [(sp.weight, z) for sp, z in readings.values() if sp.factor == "G"]
    wsum = sum(w for w, _ in members)
    expected = round(sum(w / wsum * z for w, z in members), 6)
    assert abs(g.state - expected) < 1e-6


def test_point_in_time_calculation_never_sees_later_releases():
    s = Store(":memory:")
    # UNRATE June and July readings; the July one is revised on Sep 4
    s.ingest([
        Observation("UNRATE", "2026-06-01", 4.0, "2026-06-05"),
        Observation("UNRATE", "2026-07-01", 4.0, "2026-08-07"),
        Observation("UNRATE", "2026-07-01", 4.9, "2026-09-04"),
    ] + [
        Observation("PAYEMS", f"2026-{m:02d}-01", 150_000 + 10 * m, f"2026-{m:02d}-06")
        for m in range(1, 10)
    ])
    # The revised 4.9 must be invisible at the Aug 20 boundary.
    rows = s.known_as_of("UNRATE", "2026-08-20")
    assert [(r.observation_period, r.value) for r in rows] == [
        ("2026-06-01", 4.0), ("2026-07-01", 4.0),
    ]
    # The engine's factor math uses exactly those vintages.
    early = factor_states(s, "2026-08-20")
    late = factor_states(s, "2026-09-10")
    assert early["G"].missing == ("ICSA",) and late["G"].missing == ("ICSA",)
    assert early["G"].state != late["G"].state  # the revision moved the state


def test_stale_indicator_is_treated_as_missing(tmp_path):
    s = Store(tmp_path / "stale.db")
    s.ingest([Observation("ICSA", "2026-01-03", 220_000, "2026-01-08")])
    assert "ICSA" in factor_states(s, AS_OF)["G"].missing


def test_flat_indicator_carries_zero_signal_not_missing(tmp_path):
    s = Store(tmp_path / "flat.db")
    s.ingest(_weekly("ICSA", datetime.date(2025, 8, 1), WEEKS, lambda i: 220_000))
    readings = indicator_readings(s, INDICATORS, AS_OF)
    _, z = readings["ICSA"]
    assert z == 0.0


def test_render_state_is_deterministic_bytes():
    def build(db):
        s = Store(db)
        s.ingest(_weekly("ICSA", datetime.date(2025, 8, 1), WEEKS, lambda i: 220_000))
        s.ingest(_monthly("PAYEMS", 14, lambda i: 150_000 + 20 * i))
        s.ingest(_monthly("UNRATE", 14, lambda i: 4.2))
        return render_state(compute_state(s, AS_OF))

    a = build(":memory:")
    b = build(":memory:")
    assert a.encode() == b.encode()
    assert "asof: 2026-08-25\n" in a
