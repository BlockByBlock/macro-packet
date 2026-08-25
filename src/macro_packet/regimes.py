"""Regime classification on top of the five factors.

Economic regime: softmax affinities over quadrant centers in the
Growth x Inflation plane. Continuous by construction; never probabilities.
Financial regime: descriptive combination of the rates, liquidity, and
stress states.
"""

import math

from macro_packet.specs import FLAT_THRESHOLD

# Quadrant centers (Growth, Inflation). Temperature pinned by tests in
# tests/test_regimes.py.
REGIME_CENTERS = (
    ("goldilocks", (1.0, -1.0)),
    ("reflation", (1.0, 1.0)),
    ("disinflationary_slowdown", (-1.0, -1.0)),
    ("stagflationary_slowdown", (-1.0, 1.0)),
)
SOFTMAX_TEMPERATURE = 0.5

# Financial-regime wording thresholds (state-space, tunable placeholders).
FINANCIAL_THRESHOLD = 0.25

_SLOWDOWN = ("stagflationary_slowdown", "disinflationary_slowdown")


def economic_regime(growth, inflation):
    """Return ({regime: affinity}, primary_label) at one boundary."""
    scores = {
        name: -((growth - g) ** 2 + (inflation - i) ** 2) / SOFTMAX_TEMPERATURE
        for name, (g, i) in REGIME_CENTERS
    }
    peak = max(scores.values())
    exp = {name: math.exp(s - peak) for name, s in scores.items()}
    total = sum(exp.values())
    affinities = {name: e / total for name, e in exp.items()}
    # Deterministic argmax; REGIME_CENTERS order breaks exact ties.
    order = [name for name, _ in REGIME_CENTERS]
    primary = max(order, key=lambda n: affinities[n])
    return affinities, primary


def financial_regime(rates, liquidity, stress):
    """Descriptive two-word combination of rates/liquidity/stress states."""
    if rates > FINANCIAL_THRESHOLD:
        first = "restrictive"
    elif rates < -FINANCIAL_THRESHOLD:
        first = "accommodative"
    elif liquidity > FINANCIAL_THRESHOLD:
        first = "tightening"
    elif liquidity < -FINANCIAL_THRESHOLD:
        first = "easing"
    else:
        first = "neutral"
    second = "stressed" if stress > FINANCIAL_THRESHOLD else "orderly"
    return f"{first}_{second}"


def regime_impulse(growth_now, inflation_now, growth_then, inflation_then):
    """Deteriorating/improving from affinity movement between boundaries.

    Deteriorating when the combined affinity of the two slowdown quadrants
    rose since the earlier boundary; improving otherwise.
    """
    aff_now, _ = economic_regime(growth_now, inflation_now)
    aff_then, _ = economic_regime(growth_then, inflation_then)
    bad_now = sum(aff_now[s] for s in _SLOWDOWN)
    bad_then = sum(aff_then[s] for s in _SLOWDOWN)
    return "deteriorating" if bad_now > bad_then + FLAT_THRESHOLD / 2 else "improving"


def render_regimes(growth, inflation, impulse, rates, liquidity, stress):
    """Deterministic YAML lines for both regimes with the affinity map."""
    affinities, primary = economic_regime(growth, inflation)
    lines = [
        f"econ: {primary}",
        f"econ_impulse: {impulse}",
        f"financial: {financial_regime(rates, liquidity, stress)}",
        "econ_affinity:",
    ]
    for name in sorted(affinities):
        lines.append(f"  {name}: {affinities[name]:.2f}")
    return "\n".join(lines)
