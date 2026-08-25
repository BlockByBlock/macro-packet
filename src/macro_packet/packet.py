"""The state packet: the engine's sole deliverable to the AI agent.

Assembles factors (state, impulse, confidence), both regimes with primary
affinity, drivers, contradictions, and a market-confirmation line into
compact YAML matching the source plan's §33 milestone shape. Byte-for-byte
deterministic given the same store and code.
"""

from dataclasses import dataclass

from macro_packet.diagnostics import Contradiction, Driver, contradictions, drivers
from macro_packet.engine import analyze, fmt_conf, fmt_signed, parse_date
from macro_packet.regimes import economic_regime, financial_regime, regime_impulse
from macro_packet.specs import FACTORS


@dataclass(frozen=True)
class Packet:
    """Everything the state packet says, computed at one as-of boundary."""

    as_of: str
    factors: dict          # factor -> FactorState
    impulses: dict         # factor -> up/down/flat
    econ: str              # primary economic regime label
    econ_affinity: float   # affinity of the primary label
    econ_impulse: str      # deteriorating/improving
    financial: str         # descriptive financial regime
    drivers: list          # list[Driver]
    contra: list           # list[Contradiction]
    confirm: str           # stress confirms/diverges


# Factor-specific impulse wording overrides; factors not listed use the
# plain up/down/flat vocabulary.
IMPULSE_WORDS = {
    ("L", "up"): "tighter", ("L", "down"): "easier",
    ("S", "up"): "rising", ("S", "down"): "calming",
}


def build_packet(store, as_of) -> Packet:
    """Compute every packet ingredient at an explicit as-of boundary."""
    analysis = analyze(store, as_of)
    f, b = analysis.factors, analysis.before_factors

    affinities, primary = economic_regime(f["G"].state, f["I"].state)
    econ_impulse = regime_impulse(
        f["G"].state, f["I"].state, b["G"].state, b["I"].state
    )
    return Packet(
        as_of=analysis.as_of,
        factors=f,
        impulses=analysis.impulses,
        econ=primary,
        econ_affinity=round(affinities[primary], 2),
        econ_impulse=econ_impulse,
        financial=financial_regime(f["R"].state, f["L"].state, f["S"].state),
        drivers=drivers(analysis.readings, analysis.before_readings),
        contra=contradictions(analysis.readings, f),
        confirm=_confirmation(econ_impulse, f["S"].state),
    )


def _confirmation(econ_impulse, stress_state):
    """One-line check that financial stress agrees with the economic story."""
    stress_confirms = (
        stress_state > 0 if econ_impulse == "deteriorating"
        else stress_state < 0
    )
    return "stress confirms" if stress_confirms else "stress diverges"


def render_packet(packet: Packet):
    """Deterministic compact YAML targeting ~150-300 tokens."""
    lines = [f"asof: {parse_date(packet.as_of).isoformat()}"]
    lines.append(f"econ: {packet.econ}")
    lines.append(f"econ_affinity: {packet.econ_affinity:.2f}")
    lines.append(f"econ_impulse: {packet.econ_impulse}")
    lines.append(f"financial: {packet.financial}")
    for factor in FACTORS:
        fs = packet.factors[factor]
        word = IMPULSE_WORDS.get((factor, packet.impulses[factor]), packet.impulses[factor])
        lines.append(f"{factor}: [{fmt_signed(fs.state)}, {word}, {fmt_conf(fs.confidence)}]")
    lines.append(f"confirm: {packet.confirm}")
    for section, items in (("drivers", packet.drivers), ("contra", packet.contra)):
        lines.append(f"{section}: []" if not items else f"{section}:")
        if section == "drivers":
            lines.extend(f"  - {d.series} {d.shock:+.1f}z" for d in items)
        else:
            lines.extend(f"  - {c.series} benign" for c in items)
    return "\n".join(lines) + "\n"
