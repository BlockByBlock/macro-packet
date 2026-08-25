# 02 — Indicator specs → five factor states

**What to build:** Declarative indicator configuration (factor, polarity, weight, per-indicator window years, freshness expectation) drives computation of the five factors — Growth, Inflation, Rates Pressure, Liquidity Pressure, Financial Stress — each producing a state and an impulse. Contributions are clamped z-scores against each indicator's own rolling window, multiplied by weight, and stored individually so every factor value is auditable. When an indicator is unavailable at an as-of boundary, remaining weights renormalize and the shortfall is visible. Every calculation accepts an explicit as-of boundary.

A new command, `macro-packet state`, prints the five factors as YAML from the real store.

Respect: clamped z-score contributions and renormalization policy (ADR-0004), COVID distortion handling via per-indicator windows plus default clamping (ADR-0003), glossary terms for contribution/state/impulse/as-of boundary (`CONTEXT.md`).

**Blocked by:** 01 — Scaffold + FRED fetch into point-in-time store.

**Status:** ready-for-agent

- [ ] Indicator specs are config-driven, not hard-coded into factor logic
- [ ] Polarity is respected: rising claims lowers Growth, rising yields raise Rates Pressure
- [ ] Contributions sum to the factor state; individual contributions are retrievable
- [ ] Missing indicator → renormalized weights, degraded confidence visible in output
- [ ] Point-in-time test: a calculation at a past as-of boundary never sees later releases
- [ ] Determinism test: same store + same code → identical state output bytes
