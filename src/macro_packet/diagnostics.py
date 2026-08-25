"""Drivers and contradictions: local ranking of what matters.

Both derive entirely from already-computable clamped-z readings and the
declarative specs — no new data. Weights stay hand-set guesses (deferred
calibration), so importance inherits that arbitrariness by design.
"""

import datetime

from dataclasses import dataclass

from macro_packet.engine import _date, indicator_readings
from macro_packet.specs import INDICATORS, IMPULSE_LOOKBACK_DAYS

DRIVER_CAP = 5
CONTRADICTION_CAP = 3
# A standardized move smaller than this is noise, not a driver.
DRIVER_SHOCK_FLOOR = 0.25
# A factor this weak has no direction for an indicator to contradict.
CONTRADICTION_STATE_FLOOR = 0.25


@dataclass(frozen=True)
class Driver:
    series: str
    factor: str
    shock: float  # change in polarity-applied clamped z over the lookback


@dataclass(frozen=True)
class Contradiction:
    series: str
    factor: str


def drivers(store, as_of, specs=INDICATORS):
    """Top indicators behind recent factor movement, capped at 5.

    Ranked by |standardized shock| x hand-set factor weight.
    """
    now = indicator_readings(store, specs, as_of)
    then_date = _date(as_of) - datetime.timedelta(days=IMPULSE_LOOKBACK_DAYS)
    before = indicator_readings(store, specs, then_date.isoformat())

    ranked = []
    for spec, z_now in now.values():
        _, z_before = before.get(spec.series, (None, 0.0))
        shock = z_now - z_before
        if abs(shock) < DRIVER_SHOCK_FLOOR:
            continue
        ranked.append((abs(shock) * spec.weight, Driver(spec.series, spec.factor, round(shock, 2))))
    ranked.sort(key=lambda r: (-r[0], r[1].series))
    return [d for _, d in ranked[:DRIVER_CAP]]


def contradictions(store, as_of, specs=INDICATORS):
    """Indicators disagreeing with their own factor's direction, capped at 3."""
    from macro_packet.engine import factor_states

    readings = indicator_readings(store, specs, as_of)
    states = factor_states(store, as_of, specs)

    conflicts = []
    for spec, z in readings.values():
        direction = states[spec.factor].state
        if abs(direction) < CONTRADICTION_STATE_FLOOR:
            continue
        # Opposing signs with real magnitude on both sides = genuine disagreement.
        if direction < 0 and z > DRIVER_SHOCK_FLOOR:
            strength = z * spec.weight
        elif direction > 0 and z < -DRIVER_SHOCK_FLOOR:
            strength = -z * spec.weight
        else:
            continue
        conflicts.append((strength, Contradiction(spec.series, spec.factor)))
    conflicts.sort(key=lambda r: (-r[0], r[1].series))
    return [c for _, c in conflicts[:CONTRADICTION_CAP]]
