"""Append-only point-in-time observation store backed by SQLite."""

import datetime
import sqlite3
from dataclasses import dataclass
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS observations (
    series             TEXT NOT NULL,
    observation_period TEXT NOT NULL,
    value              REAL NOT NULL,
    release_timestamp  TEXT NOT NULL,
    source             TEXT NOT NULL,
    ingested_at        TEXT NOT NULL,
    UNIQUE (series, observation_period, value, release_timestamp)
);
CREATE INDEX IF NOT EXISTS idx_observations_series_release
    ON observations (series, release_timestamp);
CREATE TABLE IF NOT EXISTS snapshots (
    asof       TEXT PRIMARY KEY,
    payload    TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS gate_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    evaluated_at  TEXT NOT NULL,
    material      INTEGER NOT NULL,
    reasons       TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS contributions (
    asof         TEXT NOT NULL,
    series       TEXT NOT NULL,
    factor       TEXT NOT NULL,
    z            REAL NOT NULL,
    weight       REAL NOT NULL,
    contribution REAL NOT NULL,
    PRIMARY KEY (asof, series)
);
"""


@dataclass(frozen=True)
class Observation:
    series: str
    observation_period: str
    value: float
    release_timestamp: str  # first date this value was knowable
    source: str = "fred"


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.executescript(_SCHEMA)

    def ingest(self, observations):
        """Insert observations; identical (series, period, value, vintage) rows are no-ops.

        Returns the number of rows actually inserted.
        """
        ingested_at = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
        with self._conn:
            cursor = self._conn.executemany(
                "INSERT OR IGNORE INTO observations VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (o.series, o.observation_period, float(o.value),
                     o.release_timestamp, o.source, ingested_at)
                    for o in observations
                ],
            )
            return cursor.rowcount

    def all_rows(self, series):
        """Full vintage history of one series, oldest release first."""
        return [
            Observation(series, p, v, r)
            for p, v, r in self._conn.execute(
                "SELECT observation_period, value, release_timestamp FROM observations"
                " WHERE series=? ORDER BY release_timestamp, observation_period",
                (series,),
            )
        ]

    def known_as_of(self, series, as_of):
        """Latest-known value per observation period among releases on/before as_of."""
        # Bare columns alongside MAX() come from the max row (documented SQLite behavior).
        return [
            Observation(series, p, v, r)
            for p, v, r in self._conn.execute(
                """
                SELECT o.observation_period, o.value, MAX(o.release_timestamp)
                FROM observations o
                WHERE o.series = ? AND o.release_timestamp <= ?
                GROUP BY o.observation_period
                ORDER BY o.observation_period
                """,
                (series, as_of),
            )
        ]

    def record_packet(self, as_of, payload, contribution_rows):
        """Atomically record a packet run: snapshot plus its contributions.

        `contribution_rows` are (series, factor, z, weight, contribution)
        tuples — plain values, so the storage layer stays ignorant of
        engine types.
        """
        created_at = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                "INSERT INTO snapshots (asof, payload, created_at) VALUES (?, ?, ?)"
                " ON CONFLICT(asof) DO UPDATE SET payload=excluded.payload,"
                " created_at=excluded.created_at",
                (as_of, payload, created_at),
            )
            self._conn.execute("DELETE FROM contributions WHERE asof = ?", (as_of,))
            self._conn.executemany(
                "INSERT INTO contributions VALUES (?, ?, ?, ?, ?, ?)",
                [(as_of, *row) for row in contribution_rows],
            )

    def latest_snapshot_before(self, as_of):
        """Most recent recorded snapshot strictly before the given boundary."""
        row = self._conn.execute(
            "SELECT asof, payload FROM snapshots WHERE asof < ?"
            " ORDER BY asof DESC LIMIT 1",
            (as_of,),
        ).fetchone()
        return {"as_of": row[0], "payload": row[1]} if row else None

    def record_gate(self, material, reasons):
        evaluated_at = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                "INSERT INTO gate_log (evaluated_at, material, reasons) VALUES (?, ?, ?)",
                (evaluated_at, 1 if material else 0, "\n".join(reasons)),
            )

    def contributions_as_of(self, as_of):
        """Stored per-indicator contributions at a boundary, ordered by factor/series."""
        return self._conn.execute(
            "SELECT series, factor, z, weight, contribution FROM contributions"
            " WHERE asof = ? ORDER BY factor, series",
            (as_of,),
        ).fetchall()
