"""Five-factor engine: clamped z-score contributions summed into factor states.

Every calculation takes an explicit as-of boundary; nothing here ever asks
for "latest" without one. All data flows through the point-in-time store,
so a past boundary can only see releases made on or before it.
"""

import datetime
import math
from dataclasses import dataclass

from macro_packet.specs import (
    FACTORS,
    FLAT_THRESHOLD,
    IMPULSE_LOOKBACK_DAYS,
    INDICATORS,
    Z_CLAMP,
)


@dataclass(frozen=True)
class Reading:
    """One indicator's standardized reading at an as-of boundary."""

    series: str
    factor: str
    z: float           # clamped, polarity-applied z-score
    weight: float      # renormalized weight actually applied
    contribution: float  # z * renormalized weight


@dataclass(frozen=True)
class FactorState:
    factor: str
    state: float       # sum of contributions
    confidence: float  # available weight / total hand-set weight
    missing: tuple     # series treated as unavailable at this boundary


def _within_window(periods, as_of_date, years):
    start = as_of_date - datetime.timedelta(days=round(365.25 * years))
    return [(p, v) for p, v in periods if start <= _date(p) <= as_of_date]


def _date(iso):
    return datetime.date.fromisoformat(iso[:10])


def indicator_readings(store, specs, as_of):
    """Clamped z readings for every available indicator at `as_of`.

    Missing indicators (no data, stale beyond freshness) are simply absent;
    callers renormalize from what is present.
    """
    as_of_date = _date(as_of)
    readings = {}
    for spec in specs:
        rows = store.known_as_of(spec.series, as_of)
        if not rows:
            continue
        latest = max(rows, key=lambda r: r.observation_period)
        if (as_of_date - _date(latest.release_timestamp)).days > spec.freshness_days:
            continue
        periods = [(r.observation_period, r.value) for r in rows]
        window = _within_window(periods, as_of_date, spec.window_years)
        if len(window) < 2:
            continue
        values = [v for _, v in window]
        mean = sum(values) / len(values)
        var = sum((v - mean) ** 2 for v in values) / len(values)
        # A flat window carries no signal but the indicator is still available.
        z = 0.0 if var == 0 else (latest.value - mean) / math.sqrt(var)
        z = spec.polarity * max(-Z_CLAMP, min(Z_CLAMP, z))
        readings[spec.series] = (spec, z)
    return readings


def factor_states(store, as_of, specs=INDICATORS):
    """Factor states at `as_of`: contributions summed per factor.

    Weights renormalize over available indicators so contributions always
    sum to the factor state; the shortfall shows up as reduced confidence.
    """
    readings = indicator_readings(store, specs, as_of)
    by_factor = {f: [] for f in FACTORS}
    for spec, z in readings.values():
        by_factor[spec.factor].append((spec, z))

    states = {}
    for factor, members in by_factor.items():
        total_weight = sum(s.weight for s in specs if s.factor == factor)
        available_weight = sum(s.weight for s, _ in members)
        contributions = []
        for spec, z in sorted(members, key=lambda m: m[0].series):
            w = spec.weight / available_weight if available_weight else 0.0
            contributions.append(Reading(spec.series, factor, round(z, 6), round(w, 6), round(z * w, 6)))
        missing = tuple(sorted(
            s.series for s in specs if s.factor == factor and s.series not in readings
        ))
        states[factor] = FactorState(
            factor=factor,
            state=round(sum(c.contribution for c in contributions), 6),
            confidence=round(available_weight / total_weight, 2) if total_weight else 0.0,
            missing=missing,
        )
    return states


def compute_state(store, as_of, specs=INDICATORS):
    """Full snapshot at `as_of`: factor states plus impulses.

    An impulse is the factor's recent rate of change: the state difference
    against the same calculation one lookback earlier, classified up/down/flat.
    """
    now = factor_states(store, as_of, specs)
    then_date = _date(as_of) - datetime.timedelta(days=IMPULSE_LOOKBACK_DAYS)
    before = factor_states(store, then_date.isoformat(), specs)

    impulses = {}
    for factor, fs in now.items():
        delta = fs.state - before[factor].state
        if abs(delta) < FLAT_THRESHOLD:
            impulses[factor] = "flat"
        else:
            impulses[factor] = "up" if delta > 0 else "down"
    return {"as_of": as_of, "factors": now, "impulses": impulses}


def render_state(snapshot):
    """Deterministic YAML rendering of a state snapshot."""
    lines = [f"asof: {_d(snapshot['as_of'])}"]
    for factor in FACTORS:
        fs = snapshot["factors"][factor]
        lines.append(f"{factor}: [{_num(fs.state)}, {snapshot['impulses'][factor]}, {_conf(fs.confidence)}]")
    missing = [s for f in FACTORS for s in snapshot["factors"][f].missing]
    if missing:
        lines.append("missing:")
        for series in missing:
            lines.append(f"  - {series}")
    return "\n".join(lines) + "\n"


def _d(as_of):
    return _date(as_of).isoformat()


def _num(x):
    return f"{x:+.2f}"


def _conf(c):
    return f"{c:.2f}"


