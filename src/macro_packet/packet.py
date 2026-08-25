"""The state packet: the engine's sole deliverable to the AI agent.

Assembles factors (state, impulse, confidence), both regimes with primary
affinity, drivers, contradictions, and a market-confirmation line into
compact YAML matching the source plan's §33 milestone shape. Byte-for-byte
deterministic given the same store and code.
"""

import datetime

from macro_packet.diagnostics import Driver, Contradiction, drivers, contradictions
from macro_packet.engine import _date, compute_state, factor_states
from macro_packet.regimes import economic_regime, financial_regime, regime_impulse
from macro_packet.specs import FACTORS, INDICATORS, IMPULSE_LOOKBACK_DAYS

# Factor-specific impulse vocabulary: same numbers, factor-native wording.
IMPULSE_WORDS = {
    "G": {"up": "up", "down": "down", "flat": "flat"},
    "I": {"up": "up", "down": "down", "flat": "flat"},
    "R": {"up": "up", "down": "down", "flat": "flat"},
    "L": {"up": "tighter", "down": "easier", "flat": "flat"},
    "S": {"up": "rising", "down": "calming", "flat": "flat"},
}

# Compact aliases are defined once here: G/I/R/L/S factor keys in output.


def build_packet(store, as_of, specs=INDICATORS):
    """Compute every packet ingredient at an explicit as-of boundary."""
    snap = compute_state(store, as_of, specs)
    f = snap["factors"]
    imp = snap["impulses"]

    then_date = _date(as_of) - datetime.timedelta(days=IMPULSE_LOOKBACK_DAYS)
    before = factor_states(store, then_date.isoformat(), specs)

    affinities, primary = economic_regime(f["G"].state, f["I"].state)
    econ_impulse = regime_impulse(
        f["G"].state, f["I"].state, before["G"].state, before["I"].state
    )
    fin = financial_regime(f["R"].state, f["L"].state, f["S"].state)

    return {
        "as_of": as_of,
        "factors": f,
        "impulses": imp,
        "econ": primary,
        "econ_affinity": round(affinities[primary], 2),
        "econ_impulse": econ_impulse,
        "financial": fin,
        "drivers": drivers(store, as_of, specs),
        "contra": contradictions(store, as_of, specs),
        "confirm": _confirmation(econ_impulse, f["S"].state),
    }


def _confirmation(econ_impulse, stress_state):
    """One-line check that financial stress agrees with the economic story."""
    stress_confirms = (
        stress_state > 0 if econ_impulse == "deteriorating"
        else stress_state < 0
    )
    return "stress confirms" if stress_confirms else "stress diverges"


def render_packet(p):
    """Deterministic compact YAML targeting ~150-300 tokens."""
    lines = [f"asof: {_date(p['as_of']).isoformat()}"]
    lines.append(f"econ: {p['econ']}")
    lines.append(f"econ_affinity: {p['econ_affinity']:.2f}")
    lines.append(f"econ_impulse: {p['econ_impulse']}")
    lines.append(f"financial: {p['financial']}")
    for factor in FACTORS:
        fs = p["factors"][factor]
        word = IMPULSE_WORDS[factor][p["impulses"][factor]]
        lines.append(f"{factor}: [{fs.state:+.2f}, {word}, {fs.confidence:.2f}]")
    lines.append(f"confirm: {p['confirm']}")
    lines.append("drivers:" if p["drivers"] else "drivers: []")
    for d in p["drivers"]:
        lines.append(f"  - {d.series} {d.shock:+.1f}z")
    lines.append("contra:" if p["contra"] else "contra: []")
    for c in p["contra"]:
        lines.append(f"  - {c.series} benign")
    return "\n".join(lines) + "\n"


def estimate_tokens(text):
    """Rough size check (chars/4); deliberately not a tokenizer."""
    return len(text) // 4
