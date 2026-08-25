from conftest import AS_OF, seed_scenario

from macro_packet.packet import build_packet, render_packet
from macro_packet.store import Store


def test_packet_matches_target_shape(quiet_store):
    packet = build_packet(quiet_store, AS_OF)
    text = render_packet(packet)
    for expected in (
        "asof: 2026-08-25",
        "econ: ",
        "econ_impulse: ",
        "financial: ",
        "G: [",
        "I: [",
        "R: [",
        "L: [",
        "S: [",
        "drivers:",
        "contra:",
    ):
        assert expected in text, f"missing {expected!r} in:\n{text}"


def test_factor_lines_use_compact_aliases_and_confidence(quiet_store):
    text = render_packet(build_packet(quiet_store, AS_OF))
    g_line = next(line for line in text.splitlines() if line.startswith("G:"))
    state, impulse, confidence = g_line.split(": ", 1)[1][1:-1].split(", ")
    assert impulse in {"up", "down", "flat", "tighter", "easier", "rising", "calming"}
    assert 0.0 <= float(confidence) <= 1.0


def test_byte_determinism_across_repeated_runs(tmp_path):
    def build(db):
        return render_packet(build_packet(seed_scenario(Store(db)), AS_OF))

    first = build(tmp_path / "a.db")
    second = build(tmp_path / "b.db")
    third = build(tmp_path / "a.db")  # same store, again
    assert first.encode() == second.encode() == third.encode()


def test_routine_packet_stays_within_token_budget(shocked_store):
    text = render_packet(build_packet(shocked_store, AS_OF))
    # ~300-token ceiling on a realistic busy day (rough estimate, not a tokenizer)
    assert len(text) // 4 <= 300, text  # rough chars/4 token estimate


def test_empty_driver_and_contra_sections_render_cleanly(quiet_store):
    text = render_packet(build_packet(quiet_store, AS_OF))
    assert "drivers: []" in text
    assert "contra: []" in text  # present, not silently omitted
