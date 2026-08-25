"""Regime classification tests: quadrant labels, affinity continuity,
softmax temperature, financial combination, impulse direction.
"""

import pytest

from macro_packet.store import Observation
from macro_packet.regimes import economic_regime, financial_regime, regime_impulse


def test_quadrant_classification_matches_clear_cut_readings():
    cases = [
        (1.2, -0.8, "goldilocks"),
        (1.2, 0.8, "reflation"),
        (-1.2, -0.8, "disinflationary_slowdown"),
        (-1.2, 0.8, "stagflationary_slowdown"),
    ]
    for growth, inflation, expected in cases:
        _, primary = economic_regime(growth, inflation)
        assert primary == expected


def test_affinities_are_continuous_at_a_border():
    # Just across the Growth axis from a center: two regimes comparable.
    near = economic_regime(0.1, -0.9)[0]
    top_two = sorted(near.values(), reverse=True)[:2]
    assert abs(top_two[0] - top_two[1]) < 0.45
    # A hair to the other side: affinities shift continuously.
    other = economic_regime(-0.1, -0.9)[0]
    for name in near:
        assert abs(near[name] - other[name]) < 0.45


def test_primary_label_is_argmax_and_affinities_sum_to_one():
    affinities, primary = economic_regime(0.3, 0.4)
    assert primary == max(affinities, key=affinities.get)
    assert sum(affinities.values()) == pytest.approx(1.0)
    assert all(0.0 <= a <= 1.0 for a in affinities.values())


def test_temperature_is_pinned_by_distance_behaviour():
    # At an exact center the two diagonal neighbors sit at distance^2=4 and
    # the far corner at 8; with T=0.5 that yields ~0.9993294.
    affinities, _ = economic_regime(1.0, -1.0)
    assert affinities["goldilocks"] == pytest.approx(0.9993294, rel=1e-6)
    # At the midpoint between two centers both share equally.
    mid = economic_regime(0.0, -1.0)[0]
    assert mid["goldilocks"] == pytest.approx(mid["disinflationary_slowdown"])


def test_financial_regime_combines_rates_liquidity_stress():
    assert financial_regime(0.6, 0.1, 0.05) == "restrictive_orderly"
    assert financial_regime(-0.6, 0.0, 0.9) == "accommodative_stressed"
    assert financial_regime(0.0, 0.6, 0.0) == "tightening_orderly"
    assert financial_regime(0.0, -0.6, 0.6) == "easing_stressed"
    assert financial_regime(0.0, 0.0, 0.0) == "neutral_orderly"


def test_regime_impulse_follows_slowdown_affinity_movement():
    # Moving from goldilocks toward stagflationary slowdown: deteriorating.
    assert regime_impulse(-0.5, 0.5, 1.0, -1.0) == "deteriorating"
    # Recovering toward goldilocks: improving.
    assert regime_impulse(1.0, -1.0, -0.5, 0.5) == "improving"
    # Unmoved: improving (no deterioration).
    assert regime_impulse(0.5, 0.2, 0.5, 0.2) == "improving"


def test_regime_output_renders_deterministically_via_state():
    """The full affinity map lives in `macro-packet state`; packet shows the
    primary affinity only. Rendering goes through engine.render_state."""
    from macro_packet.engine import analyze, render_state
    from macro_packet.store import Store

    def build(db):
        s = Store(db)
        s.ingest([Observation("DGS2", f"2026-{m:02d}-01", 3.5, f"2026-{m:02d}-02")
                  for m in range(1, 9)])
        return render_state(analyze(s, "2026-08-25"))

    a, b = build(":memory:"), build(":memory:")
    assert a.encode() == b.encode()
    assert "econ_affinity:" in a
    assert "probability" not in a.lower()
