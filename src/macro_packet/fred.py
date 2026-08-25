"""FRED fetcher producing vintage-aware observations.

Revisable series (weekly/monthly economic data) are fetched with a realtime
window so each row's realtime_start gives the date the value became known.
Daily market series have no revisions; their release timestamp is the
observation date itself (accepted point-in-time blindness, ADR-0002).
"""

import json
import urllib.error
import urllib.parse
import urllib.request

from macro_packet.store import Observation

API_URL = "https://api.stlouisfed.org/fred/series/observations"
HISTORY_START = "2006-01-01"  # ~20y window per indicator spec defaults

# The v1 indicator universe.
SERIES = (
    "ICSA", "PAYEMS", "UNRATE", "CPILFESL", "NFCI",
    "DGS2", "DGS10", "DFII10", "T5YIE", "DTWEXBGS", "DCOILWTICO", "VIXCLS",
)

# Revisable economic series are fetched with realtime vintages; everything
# else is daily market data stored with observation-date release timestamps.
REVISABLE = frozenset({"ICSA", "PAYEMS", "UNRATE", "CPILFESL", "NFCI"})


def _get_json(params):
    url = API_URL + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url) as response:
            return json.load(response)
    except urllib.error.URLError:
        # urllib puts the full URL (api_key included) in the exception text;
        # re-raise without it so keys never reach logs or tracebacks.
        raise RuntimeError(f"FRED request failed for {params['series_id']}") from None


def fetch_series(series_id, api_key):
    """Return all observations of one series as Observation rows."""
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": HISTORY_START,
    }
    # realtime_end = max date: one row per (period, vintage); the row's
    # realtime_start is the first date the value was public.
    released_at = "date"
    if series_id in REVISABLE:
        params |= {"realtime_start": HISTORY_START, "realtime_end": "9999-12-31"}
        released_at = "realtime_start"
    rows = _get_json(params)["observations"]
    return [
        Observation(series_id, r["date"], float(r["value"]), r[released_at])
        for r in rows
        if r["value"] != "."
    ]
