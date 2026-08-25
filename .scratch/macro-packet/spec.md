# macro-packet — Slice 1 Spec

**Status:** ready-for-agent

## Problem Statement

Understanding current macro conditions requires either paying an AI agent to research from scratch on every data update, or reading dozens of raw series by hand. The agent path is expensive and non-deterministic; the manual path doesn't scale. Most of what needs to happen — retrieval, normalization, standardization, aggregation, classification — is deterministic and cheap, yet today it is either not done or done by the most expensive component available (the LLM).

## Solution

A local Python CLI, `macro-packet`, that ingests free FRED data into a local point-in-time store, deterministically computes five factor states, classifies economic and financial regimes, and emits a compact **state packet** (~150–300 tokens of YAML). A **materiality gate** decides whether anything that happened since the last run justifies asking an AI agent anything at all; when it does, the CLI prints a targeted agent prompt (listing drivers and contradictions) for manual use. The division of labor is fixed: the engine answers *what changed, by how much, and how is it classified*; the agent answers only *why, and what could falsify it*.

## User Stories

1. As a solo macro analyst, I want to run one command that fetches all v1 indicators from FRED, so that my local store stays current without manual downloads.
2. As a solo macro analyst, I want each economic observation stored with its release timestamp, so that historical calculations never see information that did not exist at the time.
3. As a solo macro analyst, I want a state packet in under 300 tokens of YAML, so that I can paste it to any LLM cheaply.
4. As a solo macro analyst, I want the packet to list the top drivers of recent changes, so that I know what moved without inspecting 12 series.
5. As a solo macro analyst, I want contradictions flagged when indicators disagree with their factor's direction, so that I don't over-trust a single aggregate number.
6. As a cost-conscious user, I want the materiality gate to say "no agent call" after insignificant updates, so that I stop paying for re-research of unchanged conditions.
7. As a cost-conscious user, I want a generated agent prompt targeting only material anomalies, so that agent research is focused instead of open-ended.
8. As a skeptical analyst, I want regime affinities computed continuously rather than as hard quadrant flips, so that borderline readings don't whipsaw between labels.
9. As a skeptical analyst, I want affinities called affinities and never probabilities, so that I don't mistake uncalibrated numbers for statistics.
10. As a quant-minded user, I want indicator contributions stored individually, so that every factor value is auditable down to its inputs.
11. As a quant-minded user, I want COVID-era distortions handled by per-indicator windows and clamping, so that 2020 doesn't poison every z-score.
12. As a developer-user, I want identical store contents plus identical code to reproduce an identical packet byte-for-byte, so that results are trustworthy and debuggable.
13. As a developer-user, I want missing indicators to degrade factors gracefully with visible confidence, so that one late release doesn't break the whole packet.
14. As a CLI user, I want `packet --delta`-free stable output ordering, so that diffs between consecutive packets are meaningful.
15. As a future backtester, I want every calculation to accept an explicit as-of boundary, so that point-in-time replay is possible without code changes.

## Implementation Decisions

- **Providers:** FRED only (ADR-0001). Vintage pulls use the regular FRED observations endpoint's vintage parameters; no separate ALFRED host.
- **Storage:** single SQLite file; append-only observations keyed by `(series, observation_period, value, release_timestamp)` (ADR-0002). Market series have no vintages; accepted.
- **Indicator universe:** 12 series across five factors: ICSA, PAYEMS, UNRATE (Growth); CPILFESL, T5YIE, DCOILWTICO (Inflation); DGS2, DGS10, DFII10 (Rates); DTWEXBGS (Liquidity); NFCI + VIXCLS (Stress). Indicator specs are declarative config (source, polarity, weight, window, freshness expectation), not hard-coded logic.
- **Standardization:** clamped z-scores against each indicator's own rolling window (per-indicator `window_years`, default clamping — ADR-0003); contributions = clamped z × weight.
- **Factors:** transparent hand-set weights, no optimization; contributions stored alongside values.
- **Regimes:** economic regime from Growth × Inflation via softmax affinity over quadrant centers (never "probabilities"); financial regime from rates/liquidity/stress descriptive combination.
- **Materiality gate:** threshold triggers (factor/impulse moves, shocks, regime change) evaluated locally; thresholds tuned later from observed behaviour, not pre-calibrated.
- **Agent integration:** prompt generation only, printed for manual use. No automated agent execution, no Modes B/C, no delta packets (ADR-deferred items in `TODO.md`).
- **Packaging:** package `macro_packet`, CLI command `macro-packet`, stdlib argparse, uv-managed environment.

## Testing Decisions

- Tests exercise external behaviour through one primary seam: seed synthetic vintaged observations into SQLite → run the pipeline → assert on factors, regimes, drivers, contradictions, gate decisions, and packet output. No implementation-detail tests.
- CLI tested thin: end-to-end runs against fixture stores asserting parseable YAML and exit behaviour.
- Network fetching stays outside the test surface (contract-tested at most).
- Determinism test: same store + same code → identical packet bytes.
- Point-in-time tests: calculations at past as-of boundaries must not see later releases.

## Out of Scope

Everything deferred in `TODO.md`: DuckDB/Parquet, additional providers, evidence/delta packets, confidence/coverage/freshness triple, agent execution automation, Modes B/C, backtesting, weight calibration, hard coverage floor, token-budget CI.

## Further Notes

Vocabulary in `CONTEXT.md`; binding constraints in `docs/adr/0001`–`0004`. The §33 milestone of the source plan (`macro-state-packet-engine-implementation-plan.md`) defines the target packet shape and agent prompt shape.
