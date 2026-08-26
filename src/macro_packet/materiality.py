"""Materiality gate + agent prompt: the cost-control core.

The gate compares the current deterministic state against the last recorded
snapshot and decides whether anything material happened. Thresholds are
explicit config placeholders to be tuned from observed behaviour later
(deferred in TODO.md) — deliberately not pre-calibrated.

The agent prompt is printed for manual use only; nothing here executes an agent.
"""

import json

from macro_packet.packet import Packet

# --- threshold placeholders (tuned from observed behaviour, not pre-calibrated)
FACTOR_MOVE_THRESHOLD = 0.25   # factor state change that counts as material
SHOCK_TRIGGER = 1.5            # indicator standardized shock that counts as a shock
STRESS_JUMP_THRESHOLD = 0.5    # stress-state jump that counts as material


def packet_core(packet: Packet):
    """The comparable core of a packet: a plain dict of the material bits.

    This is the single shape both persistence and comparison use; callers
    persist `dump_core(packet)` and compare cores directly.
    """
    return {
        "econ": packet.econ,
        "financial": packet.financial,
        "impulses": dict(packet.impulses),
        "states": {k: v.state for k, v in packet.factors.items()},
        "stress": packet.factors["S"].state,
        "drivers": [{"series": d.series, "shock": d.shock} for d in packet.drivers],
        "contra": [c.series for c in packet.contra],
    }


def dump_core(packet):
    """Deterministic JSON serialization of a packet core, for storage."""
    return json.dumps(packet_core(packet), sort_keys=True)


def evaluate(current, previous):
    """Return the list of material-change reasons; empty means suppress.

    `current` is a live Packet; `previous` is {"as_of", "payload"} from the
    store. Only the stored payload crosses JSON.
    """
    if previous is None:
        return ["no previous snapshot recorded"]

    before = json.loads(previous["payload"])
    after = packet_core(current)
    reasons = []

    if before["econ"] != after["econ"]:
        reasons.append(f"regime change: {before['econ']} -> {after['econ']}")
    if before["financial"] != after["financial"]:
        reasons.append(f"financial regime change: {before['financial']} -> {after['financial']}")
    for factor, state_now in after["states"].items():
        delta = state_now - before["states"][factor]
        if abs(delta) >= FACTOR_MOVE_THRESHOLD:
            reasons.append(f"{factor} moved {delta:+.2f}")
    for factor, word_now in after["impulses"].items():
        if word_now != before["impulses"][factor]:
            reasons.append(f"{factor} impulse flipped {before['impulses'][factor]} -> {word_now}")
    if after["stress"] - before["stress"] >= STRESS_JUMP_THRESHOLD:
        reasons.append(f"stress jumped {after['stress'] - before['stress']:+.2f}")

    prev_contra = set(before["contra"])
    for c in after["contra"]:
        if c not in prev_contra:
            reasons.append(f"new contradiction: {c}")

    prev_shocks = {d["series"]: d["shock"] for d in before["drivers"]}
    for d in after["drivers"]:
        if abs(d["shock"]) >= SHOCK_TRIGGER and abs(d["shock"]) > abs(prev_shocks.get(d["series"], 0.0)):
            reasons.append(f"shock: {d['series']} {d['shock']:+.1f}z")

    return reasons


def agent_prompt(packet: Packet, reasons):
    """A targeted prompt naming only actual anomalies, for manual pasting."""
    lines = [
        "Deterministic macro state:",
        f"asof={packet.as_of}",
        f"econ={packet.econ} (affinity {packet.econ_affinity:.2f}, "
        f"{packet.econ_impulse})",
        f"financial={packet.financial}",
        "",
        "Material changes:",
    ]
    lines.extend(reasons or ["(none recorded)"])
    lines.append("")
    if packet.contra:
        lines.append("Contradictions:")
        lines.extend(f"{c.series} disagrees with its factor's direction"
                     for c in packet.contra)
        lines.append("")
    lines.append("Research only:")
    for r in research_questions(packet, reasons):
        lines.append(f"- {r}")
    lines.extend([
        "",
        "Try to falsify the classification.",
        "Keep the answer concise.",
        "Write the answer in Simplified Technical English: active voice,",
        "short sentences (max 20 words), one idea per sentence.",
    ])
    return "\n".join(lines)


def research_questions(packet: Packet, reasons):
    """Generated questions aimed at falsifying the classification — no
    generic 'research macro conditions' filler."""
    questions = []
    for d in packet.drivers:
        questions.append(
            f"What drove the {'rise' if d.shock > 0 else 'fall'} in {d.series}?"
        )
    for c in packet.contra:
        questions.append(
            f"Why does {c.series} disagree with its factor's direction — bad data, lag, or regime break?"
        )
    if any(r.startswith("regime change") for r in reasons):
        questions.append(
            "What evidence would confirm the new economic regime rather than a transient print?"
        )
    return questions
