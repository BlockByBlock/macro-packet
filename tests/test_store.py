"""Tests for the append-only point-in-time observation store."""

import sqlite3

import pytest

from macro_packet.store import Store, Observation


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "test.db")


def _obs(series, period, value, release, source="fred"):
    return Observation(
        series=series,
        observation_period=period,
        value=value,
        release_timestamp=release,
        source=source,
    )


def test_ingest_persists_observations(store):
    store.ingest(
        [
            _obs("ICSA", "2026-08-15", 218000, "2026-08-20"),
            _obs("PAYEMS", "2026-07-01", 152300, "2026-08-07"),
        ]
    )
    rows = store.all_rows("ICSA")
    assert len(rows) == 1
    row = rows[0]
    assert (row.series, row.observation_period, row.value) == ("ICSA", "2026-08-15", 218000)
    assert row.release_timestamp == "2026-08-20"


def test_reingest_is_append_only_no_duplicates(store):
    batch = [
        _obs("ICSA", "2026-08-15", 218000, "2026-08-20"),
        _obs("UNRATE", "2026-07-01", 4.2, "2026-08-07"),
    ]
    store.ingest(batch)
    store.ingest(batch)  # same vintage again: no-op
    revised = [*_obs_batch_revisions()]
    store.ingest(revised)  # new vintage of an existing period: appends
    with sqlite3.connect(store.path) as conn:
        counts = dict(conn.execute("SELECT series, COUNT(*) FROM observations GROUP BY series"))
    assert counts == {"ICSA": 2, "UNRATE": 1}


def _obs_batch_revisions():
    return [_obs("ICSA", "2026-08-15", 221000, "2026-08-27")]


def test_known_as_of_never_sees_later_releases(store):
    store.ingest(
        [
            _obs("ICSA", "2026-08-15", 218000, "2026-08-20"),
            _obs("ICSA", "2026-08-15", 221000, "2026-08-27"),
        ]
    )
    as_of_21st = store.known_as_of("ICSA", "2026-08-21")
    assert [(r.observation_period, r.value) for r in as_of_21st] == [("2026-08-15", 218000)]
    as_of_28th = store.known_as_of("ICSA", "2026-08-28")
    assert [(r.observation_period, r.value) for r in as_of_28th] == [("2026-08-15", 221000)]


def test_schema_records_source_and_ingestion_time(store):
    store.ingest([_obs("DGS10", "2026-08-22", 4.26, "2026-08-22")])
    with sqlite3.connect(store.path) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(observations)")}
        ingested_at = conn.execute(
            "SELECT ingested_at FROM observations WHERE series='DGS10'"
        ).fetchone()[0]
    assert {"series", "observation_period", "value", "release_timestamp", "source", "ingested_at"} <= cols
    assert ingested_at.endswith("+00:00") and "T" in ingested_at  # ISO UTC timestamp
