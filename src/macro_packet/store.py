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
