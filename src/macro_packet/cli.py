"""macro-packet CLI."""

import argparse
import datetime
import json
import sys
from pathlib import Path

from macro_packet.engine import analyze, render_state
from macro_packet.fred import SERIES, fetch_series
from macro_packet.materiality import agent_prompt as render_agent_prompt
from macro_packet.materiality import dump_core, evaluate
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


def _as_of(args):
    return args.as_of or datetime.date.today().isoformat()


def cmd_update(args):
    api_key = load_env().get("FRED_APIKEY")
    if not api_key:
        raise SystemExit("FRED_APIKEY not found in .env; copy .env.example and fill it in.")
    summary = run_update(args.db, lambda sid: fetch_series(sid, api_key))
    print(f"ingested {summary['inserted']} new observations across {summary['series']} series")
    return 0


def cmd_state(args):
    print(render_state(analyze(Store(args.db), _as_of(args))), end="")
    return 0


def cmd_packet(args):
    store, as_of = Store(args.db), _as_of(args)
    packet = build_packet(store, as_of)
    print(render_packet(packet), end="")
    store.save_snapshot(as_of, dump_core(packet))
    store.save_contributions(
        as_of,
        [(r.series, r.factor, r.z, r.weight, r.contribution)
         for f in packet["factors"].values() for r in f.contributions],
    )
    return 0


def _gate_reasons(store, args):
    """Shared gate evaluation for should-query-agent / agent-prompt."""
    packet = build_packet(store, _as_of(args))
    previous = store.latest_snapshot_before(_as_of(args))
    reasons = evaluate(packet, previous)
    store.record_gate(bool(reasons), reasons)
    return packet, previous, reasons


def cmd_should_query_agent(args):
    _, previous, reasons = _gate_reasons(Store(args.db), args)
    if not reasons:
        since = previous["as_of"] if previous else "(never)"
        print(f"false — no material change since {since}; no agent call")
    else:
        print("true")
        for reason in reasons:
            print(f"  - {reason}")
    return 0


def cmd_agent_prompt(args):
    packet, previous, reasons = _gate_reasons(Store(args.db), args)
    if not reasons:
        print(f"no material change since {previous['as_of']}; agent call suppressed.",
              file=sys.stderr)
        return 1
    print(render_agent_prompt(packet, reasons))
    return 0


_COMMON = argparse.ArgumentParser(add_help=False)
_COMMON.add_argument("--db", type=Path, default=DEFAULT_DB)
_DATED = argparse.ArgumentParser(add_help=False, parents=[_COMMON])
_DATED.add_argument("--as-of", default=None)

COMMANDS = {
    "update": ("fetch all series into the local store", _COMMON, cmd_update),
    "state": ("print the five factors and regimes as YAML", _DATED, cmd_state),
    "packet": ("print the compact state packet", _DATED, cmd_packet),
    "should-query-agent": ("decide whether an agent call is justified", _DATED,
                           cmd_should_query_agent),
    "agent-prompt": ("print a targeted agent prompt", _DATED, cmd_agent_prompt),
}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="macro-packet")
    sub = parser.add_subparsers(dest="command", required=True)
    handlers = {}
    for name, (help_text, parent, handler) in COMMANDS.items():
        sub.add_parser(name, help=help_text, parents=[parent])
        handlers[name] = handler

    args = parser.parse_args(argv)
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
