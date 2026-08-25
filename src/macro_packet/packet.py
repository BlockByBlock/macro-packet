"""The state packet: the engine's sole deliverable to the AI agent.

Assembles factors (state, impulse, confidence), both regimes with primary
affinity, drivers, contradictions, and a market-confirmation line into
compact YAML matching the source plan's §33 milestone shape. Byte-for-byte
deterministic given the same store and code.
"""

from macro_packet.diagnostics import contradictions, drivers
from macro_packet.engine import analyze, fmt_conf, fmt_signed, parse_date
from macro_packet.regimes import economic_regime, financial_regime, regime_impulse
from macro_packet.specs import FACTORS, INDICATORS

# Factor-specific impulse wording overrides; factors not listed use the
# plain up/down/flat vocabulary.
IMPULSE_WORD_OVERRIDES = {
    "L": {"up": "tighter", "down": "easier"},
    "S": {"up": "rising", "down": "calming"},
}


def impulse_word(factor, impulse):
    return IMPULSE_WORD_OVERRIDES.get(factor, {}).get(impulse, impulse)


def build_packet(store, as_of, specs=INDICATORS):
    """Compute every packet ingredient at an explicit as-of boundary."""
    a = analyze(store, as_of, specs)
    f, b = a.factors, a.before_factors

    affinities, primary = economic_regime(f["G"].state, f["I"].state)
    econ_impulse = regime_impulse(
        f["G"].state, f["I"].state, b["G"].state, b["I"].state
    )
    return {
        "as_of": a.as_of,
        "factors": f,
        "impulses": a.impulses,
        "econ": primary,
        "econ_affinity": round(affinities[primary], 2),
        "econ_impulse": econ_impulse,
        "financial": financial_regime(f["R"].state, f["L"].state, f["S"].state),
        "drivers": drivers(a.readings, a.before_readings, specs),
        "contra": contradictions(a.readings, f, specs),
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
    lines = [f"asof: {parse_date(p['as_of']).isoformat()}"]
    lines.append(f"econ: {p['econ']}")
    lines.append(f"econ_affinity: {p['econ_affinity']:.2f}")
    lines.append(f"econ_impulse: {p['econ_impulse']}")
    lines.append(f"financial: {p['financial']}")
    for factor in FACTORS:
        fs = p["factors"][factor]
        word = impulse_word(factor, p["impulses"][factor])
        lines.append(f"{factor}: [{fmt_signed(fs.state)}, {word}, {fmt_conf(fs.confidence)}]")
    lines.append(f"confirm: {p['confirm']}")
    for section, items in (("drivers", p["drivers"]), ("contra", p["contra"])):
        lines.append(f"{section}: []" if not items else f"{section}:")
        if section == "drivers":
            lines.extend(f"  - {d.series} {d.shock:+.1f}z" for d in items)
        else:
            lines.extend(f"  - {c.series} benign" for c in items)
    return "\n".join(lines) + "\n"
