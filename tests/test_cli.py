"""Tests for .env loading and the CLI update command (network excluded)."""

from macro_packet.cli import load_env, main, run_update
from macro_packet.fred import SERIES
from macro_packet.store import Observation, Store


def test_load_env_reads_key_value_pairs(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text('FRED_APIKEY="abc123"\n# comment\nOTHER=yes\n')
    env = load_env(env_file)
    assert env["FRED_APIKEY"] == "abc123"
    assert env["OTHER"] == "yes"


class FakeFetcher:
    """Stands in for the FRED network fetch; returns canned observations."""

    def __init__(self, batches):
        self.batches = batches
        self.calls = []

    def __call__(self, series_id):
        self.calls.append(series_id)
        return self.batches.get(series_id, [])


def test_update_command_fetches_all_series_into_store(tmp_path):
    fake = FakeFetcher(
        {
            "ICSA": [Observation("ICSA", "2026-08-15", 218000, "2026-08-20")],
            "VIXCLS": [Observation("VIXCLS", "2026-08-22", 14.8, "2026-08-22")],
        }
    )
    db = tmp_path / "macro.db"
    summary = run_update(db_path=db, fetcher=fake)
    assert set(fake.calls) == set(SERIES)
    assert summary["inserted"] == 2
    assert len(Store(db).all_rows("ICSA")) == 1


def _seed_full_store(db):
    from conftest import seed_scenario
    seed_scenario(Store(db))


def test_state_command_prints_yaml_factors(tmp_path, capsys):
    from conftest import AS_OF
    db = tmp_path / "s.db"
    _seed_full_store(db)
    assert main(["state", "--db", str(db), "--as-of", AS_OF]) == 0
    out = capsys.readouterr().out
    assert "asof:" in out and "G: [" in out and "S: [" in out


def test_packet_command_prints_and_records_snapshot(tmp_path, capsys):
    from conftest import AS_OF
    db = tmp_path / "p.db"
    _seed_full_store(db)
    assert main(["packet", "--db", str(db), "--as-of", AS_OF]) == 0
    out = capsys.readouterr().out
    assert "econ:" in out and "drivers:" in out
    store = Store(db)
    assert store.latest_snapshot_before("2026-08-26") is not None
    assert store.latest_snapshot_before(AS_OF) is None  # strictly before


def test_gate_suppresses_on_insignificant_then_fires_on_shock(tmp_path, capsys):
    from conftest import AS_OF, seed_scenario
    db = tmp_path / "g.db"
    seed_scenario(Store(db))
    # record the quiet baseline first
    assert main(["packet", "--db", str(db), "--as-of", AS_OF]) == 0
    capsys.readouterr()
    # later boundary over unchanged data -> no material change
    later = "2026-09-01"
    assert main(["should-query-agent", "--db", str(db), "--as-of", later]) == 0
    assert capsys.readouterr().out.startswith("false")

    # a fresh oil shock arrives (new vintage appended) -> gate must fire
    from macro_packet.store import Observation
    Store(db).ingest([Observation("DCOILWTICO", "2026-08-25", 120.0, "2026-08-26")])
    assert main(["should-query-agent", "--db", str(db), "--as-of", later]) == 0
    out = capsys.readouterr().out
    assert out.startswith("true")
    assert "shock: DCOILWTICO" in out


def test_agent_prompt_refuses_when_gate_suppresses(tmp_path, capsys):
    from conftest import AS_OF, seed_scenario
    db = tmp_path / "ap.db"
    seed_scenario(Store(db))
    assert main(["packet", "--db", str(db), "--as-of", AS_OF]) == 0
    capsys.readouterr()
    code = main(["agent-prompt", "--db", str(db), "--as-of", "2026-09-01"])
    captured = capsys.readouterr()
    assert code == 1
    assert "suppressed" in captured.err


def test_agent_prompt_prints_targeted_prompt_after_material_change(tmp_path, capsys):
    from conftest import AS_OF, seed_scenario
    db = tmp_path / "ap2.db"
    seed_scenario(Store(db))
    assert main(["packet", "--db", str(db), "--as-of", AS_OF]) == 0
    capsys.readouterr()
    from macro_packet.store import Observation
    Store(db).ingest([Observation("DCOILWTICO", "2026-08-25", 130.0, "2026-08-26")])
    assert main(["agent-prompt", "--db", str(db), "--as-of", "2026-09-01"]) == 0
    out = capsys.readouterr().out
    assert "Deterministic macro state:" in out
    assert "Try to falsify" in out


def test_packet_command_stores_contributions_individually(tmp_path):
    """Spec story 10: contributions retrievable, auditable down to inputs."""
    from collections import defaultdict

    from conftest import AS_OF
    from macro_packet.engine import compute_state

    db = tmp_path / "c.db"
    _seed_full_store(db)
    assert main(["packet", "--db", str(db), "--as-of", AS_OF]) == 0

    rows = Store(db).contributions_as_of(AS_OF)
    assert rows, "no contributions persisted"
    sums = defaultdict(float)
    for _series, factor, _z, _weight, contribution in rows:
        sums[factor] += contribution
    states = compute_state(Store(db), AS_OF)["factors"]
    for factor, total in sums.items():
        assert abs(total - states[factor].state) < 1e-6
