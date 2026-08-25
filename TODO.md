# TODO — Deferred by decision

Deferred machinery from §35 of the implementation plan. Each item is added back **only when its trigger fires**. Nothing here is scheduled.

## Deferred (add when earned)

- **DuckDB + Parquet** — when SQLite measurably can't cope with query volume or data size.
- **Provider abstraction layer** (BLS/BEA/Treasury/EIA) — when a second real provider is actually added.
- **Evidence packet** (~500–1,000 token secondary packet) — after a real case the compact packet could not answer.
- **Token-budget CI tests / tokenizer integration** — if packet sizes ever drift materially.
- **Delta packets (§22)** — *never* per §35.5; recorded so it isn't re-proposed. Costs statelessness for ~$0.005/call.
- **Confidence/coverage/freshness triple (§17)** — coverage and freshness answer the same question; confidence can't be calibrated at n≈4. Simplify to one staleness measure unless proven insufficient.
- **Agent Modes B (`macro-deep`) and C (`portfolio-macro`)** — after Mode A proves useful.
- **Hard coverage floor** (refuse factors below minimum input count) — if renormalized-weights behaviour ever proves too thin to trust.
- **Backtesting phase (Phase 9)** — after the live engine produces real packets worth backtesting.
- **Weight calibration** — weights stay transparent, hand-set guesses; calibrate only with observed regime behaviour.

## Accepted blind spots

- **Market-data point-in-time blindness** — VIX, WTI, DXY have no vintages; backtests are half-blind on market series by design.
- **Materiality gate thresholds** — set from observed behaviour once real packets exist, not configured in advance.

## Setup prerequisites

- [ ] FRED API key obtained and stored locally (`.env`, gitignored)
