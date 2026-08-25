"""Tests for .env loading and the CLI update command (network excluded)."""

from macro_packet.cli import load_env, run_update
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
