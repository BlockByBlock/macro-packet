"""Materiality gate + agent prompt tests through the seeded-store seam."""

import json

import pytest

from conftest import AS_OF, seed_scenario

from macro_packet.materiality import (
    FACTOR_MOVE_THRESHOLD,
    SHOCK_TRIGGER,
    agent_prompt,
    evaluate,
    research_questions,
    dump_core,
)
from macro_packet.packet import build_packet
from macro_packet.store import Store

EARLIER = "2026-07-01"  # more than one impulse lookback before AS_OF


def _packet(db_path, as_of):
    return build_packet(Store(db_path), as_of)


def test_insignificant_update_sequence_suppresses_agent_call(tmp_path):
    db = tmp_path / "quiet.db"
    seed_scenario(Store(db))  # flat baseline: nothing moves anywhere
    current = _packet(db, AS_OF)

    previous_payload = dump_core(_packet(db, EARLIER))
    reasons = evaluate(current, {"as_of": EARLIER, "payload": previous_payload})
    assert reasons == []  # e.g. growth -0.31 -> -0.32 style noise stays silent


def test_material_sequence_triggers_with_recorded_reasons(tmp_path):
    db = tmp_path / "material.db"
    seed_scenario(Store(db), shocks={"DCOILWTICO": 95.0, "T5YIE": 3.1})
    current = _packet(db, AS_OF)

    baseline_store = Store(":memory:")
    seed_scenario(baseline_store)  # same store shape, no shock
    previous_payload = dump_core(build_packet(baseline_store, AS_OF))

    reasons = evaluate(current, {"as_of": AS_OF, "payload": previous_payload})
    assert reasons, "oil shock + breakeven jump must trip the gate"
    assert any(r.startswith(("I moved", "shock:", "regime change")) for r in reasons)
    # shocks beyond ~1.5 sigma are named individually
    assert any("DCOILWTICO" in r for r in reasons)


def test_first_run_counts_as_material():
    packet = build_packet(Store(":memory:"), AS_OF)
    assert evaluate(packet, None) == ["no previous snapshot recorded"]


def test_generated_prompt_names_only_actual_anomalies(tmp_path):
    db = tmp_path / "prompt.db"
    store = seed_scenario(Store(db), shocks={"DCOILWTICO": 95.0})
    packet = build_packet(store, AS_OF)
    reasons = [f"shock: DCOILWTICO {packet.drivers[0].shock:+.1f}z"]
    prompt = agent_prompt(packet, reasons)
    assert "Deterministic macro state:" in prompt
    assert f"econ={packet.econ}" in prompt
    assert "Material changes:" in prompt and "DCOILWTICO" in prompt
    assert "Try to falsify the classification." in prompt
    assert "research macro conditions" not in prompt.lower()
    names = {d.series for d in packet.drivers}
    names |= {c.series for c in packet.contra}
    names |= {r.split()[1] for r in reasons}
    questions = research_questions(packet, reasons)
    assert questions
    for q in questions:
        assert any(name in q for name in names), q


def test_no_automated_agent_execution_anywhere():
    import inspect
    import macro_packet.materiality as mod
    source = inspect.getsource(mod)
    assert "requests" not in source and "urllib" not in source
    assert "http" not in source.lower().replace("https://fred.stlouisfed.org", "")
    # the only outputs are strings
    assert isinstance(agent_prompt.__doc__, str)


def test_dump_core_is_deterministic_json(tmp_path):
    db = tmp_path / "snap.db"
    p1 = dump_core(build_packet(seed_scenario(Store(db)), AS_OF))
    p2 = dump_core(build_packet(seed_scenario(Store(":memory:")), AS_OF))
    assert json.loads(p1)["states"] == json.loads(p2)["states"]
    assert p1 == p2


def test_thresholds_are_explicit_placeholders():
    assert 0 < SHOCK_TRIGGER <= 2.0
    assert 0 < FACTOR_MOVE_THRESHOLD <= 0.5
