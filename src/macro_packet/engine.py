"""Five-factor engine: clamped z-score contributions summed into factor states.

Every calculation takes an explicit as-of boundary; nothing here ever asks
for "latest" without one. All data flows through the point-in-time store.

Structure: `analyze` makes the single store pass (readings at the boundary
and one lookback earlier); everything downstream is a pure transform of
that analysis.
"""

import datetime
import math
from dataclasses import dataclass

from macro_packet.specs import FACTORS, INDICATORS

# Pipeline tuning (not per-indicator config).
Z_CLAMP = 3.0              # default clamping (ADR-0003)
IMPULSE_LOOKBACK_DAYS = 63  # ~ one quarter
FLAT_THRESHOLD = 0.05      # |state change| below this renders impulse flat


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
    missing: tuple = ()        # series treated as unavailable at this boundary
    contributions: tuple = ()  # individual Readings: auditable down to inputs


@dataclass(frozen=True)
class Analysis:
    """Everything derivable from one store pass at one as-of boundary."""

    as_of: str
    readings: dict         # series -> (spec, z) at as_of
    before_readings: dict  # same, one lookback earlier
    factors: dict          # factor -> FactorState
    before_factors: dict
    impulses: dict         # factor -> up/down/flat


def parse_date(iso):
    """Parse an ISO date/datetime string (public: shared across modules)."""
    return datetime.date.fromisoformat(iso[:10])


def lookback_boundary(as_of):
    """The earlier boundary one impulse-lookback before `as_of`."""
    return (parse_date(as_of) - datetime.timedelta(days=IMPULSE_LOOKBACK_DAYS)).isoformat()


def _within_window(periods, as_of_date, years):
    start = as_of_date - datetime.timedelta(days=round(365.25 * years))
    return [(p, v) for p, v in periods if start <= parse_date(p) <= as_of_date]


def indicator_readings(store, specs, as_of):
    """Clamped z readings for every available indicator at `as_of`.

    Missing indicators (no data, stale beyond freshness) are simply absent;
    callers renormalize from what is present.
    """
    as_of_date = parse_date(as_of)
    readings = {}
    for spec in specs:
        rows = store.known_as_of(spec.series, as_of)
        if not rows:
            continue
        latest = max(rows, key=lambda r: r.observation_period)
        if (as_of_date - parse_date(latest.release_timestamp)).days > spec.freshness_days:
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


def factor_states(readings):
    """Factor states from a set of readings: contributions summed per factor.

    Weights renormalize over available indicators so contributions always
    sum to the factor state; the shortfall shows up as reduced confidence.
    """
    by_factor = {f: [] for f in FACTORS}
    for spec, z in readings.values():
        by_factor[spec.factor].append((spec, z))

    total_weights = {f: sum(s.weight for s in INDICATORS if s.factor == f) for f in FACTORS}
    states = {}
    for factor, members in by_factor.items():
        available_weight = sum(s.weight for s, _ in members)
        contributions = []
        for spec, z in sorted(members, key=lambda m: m[0].series):
            w = spec.weight / available_weight if available_weight else 0.0
            contributions.append(Reading(spec.series, factor, round(z, 6), round(w, 6), round(z * w, 6)))
        missing = tuple(sorted(
            s.series for s in INDICATORS if s.factor == factor
            and s.series not in readings
        ))
        total_weight = total_weights[factor]
        states[factor] = FactorState(
            factor=factor,
            state=round(sum(c.contribution for c in contributions), 6),
            confidence=round(available_weight / total_weight, 2) if total_weight else 0.0,
            missing=missing,
            contributions=tuple(contributions),
        )
    return states


def factor_impulses(factors, before_factors):
    """Impulse = recent rate of change of the state, classified up/down/flat."""
    impulses = {}
    for factor, fs in factors.items():
        delta = fs.state - before_factors[factor].state
        impulses[factor] = "flat" if abs(delta) < FLAT_THRESHOLD \
            else ("up" if delta > 0 else "down")
    return impulses


def analyze(store, as_of):
    """The single store pass every downstream computation consumes."""
    readings = indicator_readings(store, INDICATORS, as_of)
    before_readings = indicator_readings(store, INDICATORS, lookback_boundary(as_of))
    factors = factor_states(readings)
    before_factors = factor_states(before_readings)
    return Analysis(
        as_of=as_of,
        readings=readings,
        before_readings=before_readings,
        factors=factors,
        before_factors=before_factors,
        impulses=factor_impulses(factors, before_factors),
    )


def fmt_signed(x):
    return f"{x:+.2f}"


def fmt_conf(c):
    return f"{c:.2f}"


