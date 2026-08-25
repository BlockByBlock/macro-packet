"""macro-packet CLI."""

import argparse
import datetime
import sys
from pathlib import Path

from macro_packet.engine import compute_state, render_state
from macro_packet.fred import SERIES, fetch_series
from macro_packet.materiality import agent_prompt as render_agent_prompt
from macro_packet.materiality import evaluate, snapshot_payload
from macro_packet.packet import build_packet, render_packet
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


def _default_as_of():
    return datetime.date.today().isoformat()


def main(argv=None):
    parser = argparse.ArgumentParser(prog="macro-packet")
    sub = parser.add_subparsers(dest="command", required=True)

    p_update = sub.add_parser("update", help="fetch all series into the local store")
    p_update.add_argument("--db", type=Path, default=DEFAULT_DB)

    p_state = sub.add_parser("state", help="print the five factors as YAML")
    p_state.add_argument("--db", type=Path, default=DEFAULT_DB)
    p_state.add_argument("--as-of", default=None)

    p_packet = sub.add_parser("packet", help="print the compact state packet")
    p_packet.add_argument("--db", type=Path, default=DEFAULT_DB)
    p_packet.add_argument("--as-of", default=None)

    p_gate = sub.add_parser(
        "should-query-agent", help="decide whether an agent call is justified")
    p_gate.add_argument("--db", type=Path, default=DEFAULT_DB)
    p_gate.add_argument("--as-of", default=None)

    p_prompt = sub.add_parser("agent-prompt", help="print a targeted agent prompt")
    p_prompt.add_argument("--db", type=Path, default=DEFAULT_DB)
    p_prompt.add_argument("--as-of", default=None)

    args = parser.parse_args(argv)

    if args.command == "update":
        api_key = load_env().get("FRED_APIKEY")
        if not api_key:
            raise SystemExit("FRED_APIKEY not found in .env; copy .env.example and fill it in.")
        summary = run_update(args.db, lambda sid: fetch_series(sid, api_key))
        print(f"ingested {summary['inserted']} new observations across {summary['series']} series")
        return 0

    as_of = args.as_of or _default_as_of()
    store = Store(args.db)

    if args.command == "state":
        print(render_state(compute_state(store, as_of)), end="")
        return 0

    packet = build_packet(store, as_of)

    if args.command == "packet":
        print(render_packet(packet), end="")
        store.save_snapshot(as_of, snapshot_payload(packet))
        store.save_contributions(
            as_of,
            [c for f in packet["factors"].values() for c in f.contributions],
        )
        return 0

    previous = store.latest_snapshot_before(as_of)
    reasons = evaluate(packet, previous)
    material = bool(reasons)
    store.record_gate(material, reasons)

    if args.command == "should-query-agent":
        if not material:
            print(f"false — no material change since "
                  f"{previous['as_of'] if previous else '(never)'}; no agent call")
        else:
            print("true")
            for reason in reasons:
                print(f"  - {reason}")
        return 0

    # agent-prompt
    if not material:
        print(f"no material change since {previous['as_of']}; agent call suppressed.",
              file=sys.stderr)
        return 1
    print(render_agent_prompt(packet, reasons))
    return 0


if __name__ == "__main__":
    sys.exit(main())
