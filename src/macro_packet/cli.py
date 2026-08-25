"""macro-packet CLI."""

import argparse
import sys
from pathlib import Path

from macro_packet.fred import SERIES, fetch_series
from macro_packet.store import Store

DEFAULT_DB = Path("data/macro.db")
ENV_FILE = Path(".env")


def load_env(path=ENV_FILE):
    """Parse a simple KEY=VALUE .env file."""
    env = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def run_update(db_path, fetcher):
    """Fetch every configured series and ingest into the store.

    `fetcher` maps series_id -> list[Observation]. Returns a small summary.
    """
    store = Store(db_path)
    inserted = sum(store.ingest(fetcher(series_id)) for series_id in SERIES)
    return {"series": len(SERIES), "inserted": inserted}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="macro-packet")
    sub = parser.add_subparsers(dest="command", required=True)
    update = sub.add_parser("update", help="fetch all series into the local store")
    update.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args(argv)

    api_key = load_env().get("FRED_APIKEY")
    if not api_key:
        raise SystemExit("FRED_APIKEY not found in .env; copy .env.example and fill it in.")

    summary = run_update(args.db, fetcher=lambda series_id: fetch_series(series_id, api_key))
    print(f"ingested {summary['inserted']} new observations across {summary['series']} series")
    return 0


if __name__ == "__main__":
    sys.exit(main())
