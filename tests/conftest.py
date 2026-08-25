"""Shared synthetic-data seeding for pipeline tests.

Every helper seeds vintaged observations directly into SQLite — the
primary seam. Weekly series span 2025-08..2026-08 so their last release
is fresh at the canonical AS_OF boundary.
"""

import datetime

import pytest

from macro_packet.store import Observation, Store

AS_OF = "2026-08-25"
WEEKS = 56
START = datetime.date(2025, 8, 1)


def weekly(series, value_fn, start=START, weeks=WEEKS, release_lag_days=4):
    return [
        Observation(
            series,
            (start + datetime.timedelta(days=7 * i)).isoformat(),
            value_fn(i),
            (start + datetime.timedelta(days=7 * i + release_lag_days)).isoformat(),
        )
        for i in range(weeks)
    ]


def monthly(series, months=14, value_fn=lambda i: 0.0,
            start=datetime.date(2025, 7, 1), release_day=6):
    obs = []
    for i in range(months):
        y, m = divmod(start.month - 1 + i, 12)
        period = datetime.date(start.year + y, m + 1, min(start.day, 28))
        obs.append(Observation(
            series, period.isoformat(), value_fn(i),
            period.replace(day=min(release_day, 28)).isoformat(),
        ))
    return obs


def seed_scenario(store, shocks=None):
    """Full twelve-series baseline; `shocks` overrides final weekly values."""
    shocks = shocks or {}
    baselines = {
        "ICSA": 220_000, "DGS2": 3.5, "DGS10": 4.0, "DFII10": 2.0,
        "VIXCLS": 15.0, "DTWEXBGS": 110.0, "NFCI": 0.0, "T5YIE": 2.3,
        "DCOILWTICO": 70.0, "CPILFESL": 300.0, "UNRATE": 4.2,
    }
    for series, base in baselines.items():
        store.ingest(weekly(series, lambda i, b=base, s=series:
                            shocks.get(s, b) if i == WEEKS - 1 else b))
    payems_last = shocks.get("PAYEMS", 150_000)
    store.ingest(monthly("PAYEMS", value_fn=lambda i: 150_000 if i < 13 else payems_last))
    return store


@pytest.fixture
def quiet_store(tmp_path):
    """A store where nothing material is happening."""
    return seed_scenario(Store(tmp_path / "quiet.db"))


@pytest.fixture
def shocked_store(tmp_path):
    """A store with a material oil shock plus an inflation jump."""
    return seed_scenario(Store(tmp_path / "shocked.db"), shocks={
        "DCOILWTICO": 95.0,
        "T5YIE": 3.1,
    })
