"""Declarative indicator configuration for the five-factor engine.

Specs are data, not logic: factor membership, polarity, hand-set weight,
per-indicator standardization window, and a freshness expectation (how
stale an observation may be at the as-of boundary before the indicator is
treated as unavailable). Factor code never reads series ids directly.
"""

from dataclasses import dataclass

FACTORS = ("G", "I", "R", "L", "S")


@dataclass(frozen=True)
class IndicatorSpec:
    series: str          # FRED series id; also the display name in packets
    factor: str          # one of FACTORS
    polarity: int        # +1: rising value raises the factor; -1: lowers it
    weight: float        # hand-set weight within its factor (deferred calibration)
    window_years: float  # rolling standardization window length
    freshness_days: int  # max age of latest release before indicator counts missing


INDICATORS = (
    IndicatorSpec("ICSA",      "G", -1, 0.40, 5.0, 14),
    IndicatorSpec("PAYEMS",    "G", +1, 0.35, 8.0, 45),
    IndicatorSpec("UNRATE",    "G", -1, 0.25, 8.0, 45),
    IndicatorSpec("CPILFESL",  "I", +1, 0.50, 6.0, 60),
    IndicatorSpec("T5YIE",     "I", +1, 0.30, 3.0, 10),
    IndicatorSpec("DCOILWTICO","I", +1, 0.20, 2.0, 7),
    IndicatorSpec("DGS2",      "R", +1, 0.40, 3.0, 7),
    IndicatorSpec("DGS10",     "R", +1, 0.35, 3.0, 7),
    IndicatorSpec("DFII10",    "R", +1, 0.25, 3.0, 7),
    IndicatorSpec("DTWEXBGS",  "L", +1, 1.00, 3.0, 7),
    IndicatorSpec("NFCI",      "S", +1, 0.55, 5.0, 10),
    IndicatorSpec("VIXCLS",    "S", +1, 0.45, 3.0, 7),
)
