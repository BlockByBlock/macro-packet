"""Driver and contradiction tests through the seeded-store seam.

The pipeline is: one `analyze` pass, then pure ranking functions.
"""

import datetime

from macro_packet.diagnostics import (
    DRIVER_SHOCK_FLOOR,
    contradictions,
    drivers,
)
from macro_packet.engine import analyze, indicator_readings
from macro_packet.specs import INDICATORS
from macro_packet.store import Observation, Store

AS_OF = "2026-08-25"
WEEKS = 56
START = datetime.date(2025, 8, 1)


def _weekly(series, value_fn):
    return [
        Observation(
            series,
            (START + datetime.timedelta(days=7 * i)).isoformat(),
            value_fn(i),
            (START + datetime.timedelta(days=7 * i + 4)).isoformat(),
        )
        for i in range(WEEKS)
    ]


def _shock(s, series, base, last):
    s.ingest(_weekly(series, lambda i, b=base, l=last: l if i == WEEKS - 1 else b))


def _flat(s, series, value):
    s.ingest(_weekly(series, lambda i, v=value: v))


def _seed_growth(store, claims_last=None, payems_last=None):
    """Growth factor inputs: benign baseline, optional final-reading shocks."""
    store.ingest(_weekly("ICSA", lambda i: claims_last or 220_000 if i == WEEKS - 1 else 220_000))
    store.ingest([
        Observation("PAYEMS", f"2026-{m:02d}-01", 150_000 if m < 8 else (payems_last or 150_000),
                    f"2026-{m:02d}-06")
        for m in range(1, 9)
    ])
    _flat(store, "UNRATE", 4.2)


def test_driver_list_capped_at_five_and_ranked_by_documented_formula():
    s = Store(":memory:")
    # Five market series all shock upward at the boundary.
    bases = {"DGS2": 3.5, "DGS10": 4.0, "DFII10": 1.8, "VIXCLS": 15.0, "DTWEXBGS": 110.0}
    lasts = {"DGS2": 4.6, "DGS10": 4.9, "DFII10": 2.6, "VIXCLS": 40.0, "DTWEXBGS": 125.0}
    for series, base in bases.items():
        _shock(s, series, base, lasts[series])
    a = analyze(s, AS_OF)
    result = drivers(a.readings, a.before_readings)

    assert len(result) == 5  # capped even though five is all we fed it
    # documented formula: rank by |standardized shock| x hand-set weight,
    # with the earlier-boundary reading at a flat baseline contributing z=0
    readings = dict(indicator_readings(s, INDICATORS, AS_OF))
    specs = {series: spec for series, (spec, _) in readings.items()}
    zs = {series: z for series, (_, z) in readings.items()}
    expected_order = sorted(zs, key=lambda n: (-(abs(zs[n] - 0.0)) * specs[n].weight, n))
    assert [d.series for d in result][: len(expected_order)] == list(expected_order)[:5]


def test_drivers_apply_polarity_and_rank_by_shock_times_weight():
    s = Store(":memory:")
    _seed_growth(s, claims_last=400_000)
    a = analyze(s, AS_OF)
    top = drivers(a.readings, a.before_readings)[0]
    assert top.series == "ICSA"
    assert top.shock <= -DRIVER_SHOCK_FLOOR  # claims spike reads negative via polarity -1


def test_insignificant_days_yield_empty_driver_lists():
    s = Store(":memory:")
    _seed_growth(s)  # everything steady
    a = analyze(s, AS_OF)
    assert drivers(a.readings, a.before_readings) == []
    assert contradictions(a.readings, a.factors) == []


def test_contradiction_flags_cross_signal_disagreement():
    store = Store(":memory:")
    # Claims spike drags Growth down, yet payrolls printed strong.
    _seed_growth(store, claims_last=400_000, payems_last=165_000)
    a = analyze(store, AS_OF)
    names = [c.series for c in contradictions(a.readings, a.factors)]
    assert names[0] == "PAYEMS"
    assert len(names) <= 3


def test_contradictions_capped_at_three_strongest_only():
    s = Store(":memory:")

    def shock(series, base, last):
        _shock(s, series, base, last)

    # R positive: 2y and 10y yields spike while the real yield eases.
    shock("DGS2", 3.5, 4.8)
    shock("DGS10", 4.0, 5.3)
    shock("DFII10", 2.0, 1.0)
    # S positive: VIX jumps while NFCI eases.
    shock("VIXCLS", 15.0, 40.0)
    shock("NFCI", 0.0, -0.4)
    # I positive: breakevens rise while oil plunges.
    shock("T5YIE", 2.3, 2.9)
    shock("DCOILWTICO", 70.0, 55.0)
    _flat(s, "CPILFESL", 300.0)
    # L and G stay quiet.
    _flat(s, "DTWEXBGS", 110.0)
    _flat(s, "ICSA", 220_000)
    s.ingest([Observation("PAYEMS", f"2026-{m:02d}-01", 150_000, f"2026-{m:02d}-06")
              for m in range(1, 9)])
    _flat(s, "UNRATE", 4.2)

    a = analyze(s, AS_OF)
    result = contradictions(a.readings, a.factors)
    assert len(result) == 3  # capped at 3 strongest conflicts
    assert {c.factor for c in result} <= {"R", "S", "I"}
    assert {c.series for c in result} == {"DFII10", "DCOILWTICO", "VIXCLS"}
