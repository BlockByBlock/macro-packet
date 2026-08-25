# Macro State Packet Engine — Implementation Plan

## 1. Objective

Build a small local deterministic macro processor that produces a **compact macro state packet** for an AI agent.

The local software should do all work that is deterministic and cheap locally:

- data retrieval
- normalization
- rolling statistics
- trend calculation
- factor construction
- regime classification
- anomaly detection
- contradiction detection
- freshness/coverage checks
- materiality gating
- compact packet generation

The AI agent should receive only the minimum information needed to:

1. explain unusual changes;
2. research current context;
3. challenge/falsify the deterministic regime;
4. identify missing context;
5. summarize what matters.

The design priority is:

> **Minimize LLM token usage without losing decision-relevant macro information.**

Core principle:

> **Use local software for compression. Use the agent for ambiguity.**

---

## 2. Target Architecture

```text
                    FREE / LOW-COST DATA
                            │
             ┌──────────────┼──────────────┐
             ↓              ↓              ↓
        Economic data    Market data    Release data
             │              │              │
             └──────────────┼──────────────┘
                            ↓
                   ┌────────────────┐
                   │  macro-regime  │
                   │ LOCAL SOFTWARE │
                   └───────┬────────┘
                           │
                    deterministic
                     calculations
                           │
                           ↓
                  MATERIALITY GATE
                           │
                 ┌─────────┴─────────┐
                 ↓                   ↓
             no material          material
               change              change
                 │                   │
                 ↓                   ↓
               STOP          MACRO STATE PACKET
                                  ~150–300 tokens
                                        │
                                        ↓
                                    AI AGENT
                                        │
                              targeted web research
                                 only if necessary
                                        │
                                        ↓
                               CONTEXT + CHALLENGE
                                        │
                                        ↓
                              cached context result
```

The agent should **not** receive raw historical series unless explicitly required.

---

## 3. Repository Scope

Create a standalone local Python project:

```text
macro-regime/
├── src/
│   └── macro_regime/
│       ├── providers/
│       ├── storage/
│       ├── transforms/
│       ├── indicators/
│       ├── factors/
│       ├── regimes/
│       ├── diagnostics/
│       ├── materiality/
│       ├── packet/
│       └── cli/
├── config/
├── data/
├── snapshots/
├── context_cache/
├── tests/
├── docs/
└── pyproject.toml
```

Do not build a web service initially.

Start as:

* Python library
* CLI
* local data store
* versioned snapshot writer

---

## 4. Explicit Non-Goals

Do **not** include in v1:

* portfolio optimization
* stock selection
* trade recommendations
* asset-return forecasting
* LLM-based regime classification
* LLM-based scoring
* autonomous agents inside the local engine
* full news ingestion
* large vector databases
* unnecessary dashboards
* hundreds of macro indicators

The engine's job is to create a **small, trustworthy state representation**.

---

## 5. V1 Macro Dimensions

Use five dimensions:

1. Growth
2. Inflation Pressure
3. Rates / Policy Pressure
4. USD / Liquidity Pressure
5. Financial Stress

Keep Growth and Inflation conceptually separate from financial conditions.

Economic regime:

```text
Growth × Inflation
```

Financial regime:

```text
Rates + Liquidity + Stress
```

Do **not** produce one overall "Macro Score".

---

## 6. Initial Indicator Universe

Keep v1 deliberately small.

Target approximately **15–20 indicators**.

### Growth

Candidate inputs:

* Initial Jobless Claims
* Continuing Claims
* Nonfarm Payrolls
* Unemployment Rate
* ISM Manufacturing New Orders
* ISM Services or composite activity indicator
* Retail Sales or real consumer spending
* HY spreads as secondary confirmation

### Inflation

Candidate inputs:

* Core CPI
* Core PCE
* CPI/PCE 3-month annualized trend where available
* Wage growth
* 5Y or 5Y5Y breakeven inflation
* WTI

### Rates / Policy

Candidate inputs:

* Fed Funds target / effective rate
* 2Y Treasury
* 10Y Treasury
* 30Y Treasury
* 10Y real yield
* 2s10s
* optional Fed expectations proxy

### USD / Liquidity

Candidate inputs:

* DXY
* USDJPY
* selected financial conditions index
* optional reserve/liquidity indicator later

### Financial Stress

Candidate inputs:

* HY spread
* IG spread
* CCC spread if accessible
* VIX
* MOVE if accessible

Do not expand the universe until v1 proves useful.

---

## 7. Data Source Strategy

Prefer authoritative/free sources.

Possible providers:

```text
BLS
BEA
Federal Reserve
US Treasury
EIA
FRED / ALFRED
market-data provider
```

Provider interfaces should abstract the source.

Conceptual interface:

```text
get_series(series_id, as_of)
get_latest(series_id, as_of)
get_release_history(series_id)
```

Do not tightly couple factor logic to a provider.

---

## 8. Point-in-Time Requirement

Every calculation must accept an explicit:

```text
as_of_timestamp
```

Never ask:

```text
latest()
```

without an as-of boundary.

Instead:

```text
latest_known_as_of(timestamp)
```

Store enough metadata to distinguish:

* observation period
* release timestamp
* first-reported value
* later revision
* source
* ingestion timestamp

Historical backtesting must only see information available at the requested time.

---

## 9. Local Storage

Use a simple local analytical store.

Recommended initial stack:

```text
DuckDB + Parquet
```

Possible logical tables:

```text
series_metadata
observations
releases
market_prices
indicator_states
factor_states
regime_states
snapshots
context_cache
```

Do not over-engineer relational normalization.

Prioritize:

* point-in-time querying
* reproducibility
* append-only history
* easy inspection

---

## 10. Indicator Specification Layer

Each indicator should have an explicit configuration.

Example:

```yaml
id: initial_claims

factor: growth

source:
  provider: fred
  series: ICSA

frequency: weekly

transformations:
  level_percentile:
    window_years: 10

  change_4w: true

  change_13w: true

direction:
  rising_is: negative

freshness:
  expected_days: 7

weight: 0.20
```

Do not hard-code transformations into factor logic.

Each indicator spec should define:

* source
* factor
* frequency
* transformations
* polarity
* weight
* freshness expectation
* optional shock thresholds

---

## 11. Indicator Transformations

Do not force every series through the same transformation.

Use transformation families.

### Economic Data

Possible outputs:

```text
level
YoY
3M annualized
short-term trend
acceleration
revision
```

### Market Prices

Possible outputs:

```text
1M change
3M change
rolling percentile
volatility-adjusted shock
```

### Treasury Yields

Prefer:

```text
level
1M change in bp
3M change in bp
curve changes
real vs nominal decomposition
```

Do not primarily use MA50/MA200 for yields.

### Equity-Market Trend

For SPX market confirmation only:

```text
distance_to_200d
200d_slope
distance_to_50d
50d_slope
```

Interpretation:

```text
200D → structural state
50D  → intermediate impulse
```

Do not use SPX trend to define the economic regime.

---

## 12. State and Impulse

Every factor must produce at least:

```text
state
impulse
```

Example:

```yaml
growth:
  state: -0.31
  impulse: -0.48
```

Definitions:

* `state` = current underlying condition
* `impulse` = recent direction / rate of change

Optionally add later:

```text
persistence
```

Example:

```yaml
inflation:
  state: 0.42
  impulse: 0.51
  persistence_months: 3
```

---

## 13. Factor Construction

Do not optimize weights initially.

Use transparent configurable weights.

Example:

```text
Growth =
Σ standardized_indicator_contribution × weight
```

Store each contribution.

Example:

```yaml
growth:
  value: -0.31

  contributions:
    payrolls: -0.12
    claims: +0.05
    ism_new_orders: -0.14
    retail_sales: -0.03
    credit: -0.07
```

This enables driver and contradiction extraction without an LLM.

---

## 14. Economic Regime

Use Growth × Inflation.

Initial quadrants:

```text
Growth ↑ + Inflation ↓ = Goldilocks
Growth ↑ + Inflation ↑ = Reflation
Growth ↓ + Inflation ↓ = Disinflationary Slowdown
Growth ↓ + Inflation ↑ = Stagflationary Slowdown
```

Avoid brittle hard boundaries.

Prefer continuous regime affinity.

Example:

```yaml
economic_regime:
  primary: stagflationary_slowdown

  affinity:
    goldilocks: 0.08
    reflation: 0.17
    slowdown: 0.21
    stagflationary_slowdown: 0.54
```

Until empirically calibrated, call these:

* affinity
* membership
* classification strength

Do not call them probabilities.

---

## 15. Financial Regime

Keep Rates, Liquidity and Stress visible separately.

Classify into descriptive states such as:

```text
easing_orderly
restrictive_orderly
easing_stressed
restrictive_stressed
```

Example:

```yaml
financial_regime:
  primary: restrictive_orderly

rates_pressure: 0.61
liquidity_pressure: 0.18
stress: 0.09
```

Important principle:

```text
tight ≠ broken
```

---

## 16. Contradiction Detection

Do this locally.

Example:

Growth score is negative, but:

```text
claims = benign
credit = benign
retail_sales = positive
```

Generate:

```yaml
contradictions:
  - initial_claims_benign
  - hy_spreads_benign
```

Do not send every indicator to the agent.

Only send the strongest conflicting signals.

---

## 17. Confidence, Coverage and Freshness

Track separately.

Example:

```yaml
growth:
  confidence: 0.76
  coverage: 0.91
  freshness: 0.88
```

Definitions:

### Confidence

How strongly available indicators agree.

### Coverage

Fraction of expected indicator input currently available.

### Freshness

How current those inputs are relative to their normal release frequency.

Do not combine them into one opaque score.

---

## 18. Driver Ranking

The agent should not need to inspect all indicators.

Calculate local driver importance.

Possible initial formula:

```text
importance =
abs(change_in_contribution)
× configured_weight
```

or:

```text
importance =
abs(standardized_shock)
× factor_weight
```

Keep the top:

```text
3–5 drivers
```

Example:

```yaml
drivers:
  - id: wti
    shock_z: 2.1
    effect: inflation_up

  - id: us30y
    change_1m_bp: 41
    effect: rates_pressure_up

  - id: payroll_trend
    shock_z: -1.2
    effect: growth_down
```

---

## 19. Materiality Gate

This is critical for token efficiency.

Do not invoke the AI agent after every data update.

Trigger an AI context/challenge run only if one or more conditions occur.

Example triggers:

```text
economic regime changes
financial regime changes
factor state changes > configured threshold
factor impulse changes > configured threshold
indicator shock > 1.5σ
financial stress jumps materially
cross-asset contradiction appears
previously cached context becomes stale
```

Example:

```text
Growth -0.31 → -0.32
Inflation +0.42 → +0.41

NO AGENT CALL
```

versus:

```text
WTI +8%
Inflation +0.41 → +0.55
30Y +35bp

AGENT CALL
```

---

## 20. Macro State Packet

The default packet should be extremely compact.

Target:

```text
~150–300 tokens
```

Example:

```yaml
asof: 2026-08-25

econ: stagflationary_slowdown
econ_impulse: deteriorating
econ_affinity: 0.54

financial: restrictive_orderly

G: [-0.31, down, 0.76]
I: [+0.42, up, 0.83]
R: [+0.61, up, 0.91]
L: [+0.18, tighter, 0.69]
S: [+0.09, flat, 0.86]

drivers:
  - WTI +2.1z
  - US30Y +41bp/1m
  - payroll_trend -1.2z

contra:
  - claims benign
  - HY spreads benign

market:
  SPX: structural_up, impulse_down
  DXY: down
  USDJPY: down
```

The compact aliases are intentional.

The AI system prompt can define:

```text
G = Growth
I = Inflation
R = Rates
L = Liquidity
S = Stress
```

once rather than repeating verbose labels every call.

---

## 21. Evidence Packet

Generate a second, larger packet but do not send it by default.

Target:

```text
~500–1,000 tokens
```

Use only when:

* the agent needs to resolve ambiguity;
* a deep macro assessment is requested;
* the regime changed materially;
* the user explicitly asks for detailed evidence.

Example:

```yaml
growth:
  payroll:
    latest: -23k
    trend_3m: weakening
    z: -1.2

  claims:
    latest: 206k
    trend_4w: flat
    z: 0.2

inflation:
  core_cpi_yoy: 2.5
  core_cpi_3m_ann: 2.8
  wti_1m_pct: 12.1
  breakeven_1m_bp: 18

rates:
  us2y: 3.99
  us10y: 4.69
  us30y: 5.23
  us10y_1m_bp: 12
  us30y_1m_bp: 41
```

---

## 22. Delta-First Packet Design

When the previous packet is known, send changes rather than full state where possible.

Example:

```yaml
asof: 2026-08-26

unchanged:
  econ: stagflationary_slowdown
  financial: restrictive_orderly

delta:
  I: +0.42 -> +0.55
  R: +0.61 -> +0.68

new_drivers:
  - WTI +2.8z
  - breakeven +1.6z

resolved:
  - none
```

This can reduce recurring prompt size substantially.

---

## 23. Context Cache

Store previously researched event context locally.

Example:

```yaml
id: middle_east_oil_shock

first_seen: 2026-08-18
last_checked: 2026-08-24

status: active

interpretation:
  primary: supply_disruption
  affects:
    - inflation
    - growth

confidence: high
```

The packet can then say:

```text
known_context:
oil_shock=active
```

Do not ask the agent to rediscover the same explanation every day.

Refresh only if:

```text
price behavior changes materially
event escalates
event resolves
new contradiction emerges
cache expires
```

---

## 24. Agent Request Generator

The local software should generate a targeted agent task based on anomalies.

Bad:

```text
Research current macro conditions.
```

Better:

```text
Current deterministic state:

econ=stagflationary_slowdown
financial=restrictive_orderly

material changes:
- WTI +2.1z
- US30Y +41bp/1m
- DXY -1.0z

contradictions:
- claims benign
- HY benign

Research only:
1. Why is oil rising?
2. Why is the long end selling off?
3. Why is DXY falling despite higher yields?
4. Does credit confirm macro deterioration?

Try to falsify the current regime classification.
Return concise context only.
```

The agent should investigate only questions generated by the local system.

---

## 25. Agent Modes

Support three modes.

### Mode A — `macro-update`

Routine and cheap.

Input:

```text
compact state packet
+ targeted anomaly questions
```

Output:

```text
context
challenge
whether classification remains plausible
```

Use when the materiality gate triggers.

### Mode B — `macro-deep`

Occasional.

Input:

```text
compact packet
+ evidence packet
```

Use:

* weekly;
* after major CPI/payroll/FOMC/geopolitical events;
* on demand.

The agent may perform broader web research.

### Mode C — `portfolio-macro`

Only when portfolio interpretation is requested.

Input:

```text
macro packet
+ compressed portfolio exposure packet
```

Do not send full holdings unless needed.

Example:

```yaml
portfolio:
  alignment: -0.28

  factor:
    momentum: 1.2
    quality: 0.7
    value: -0.2
    lowvol: -0.6
    beta: 0.9
```

---

## 26. Agent Output Contract

Keep agent output structured enough to cache.

Example:

```yaml
asof: 2026-08-25

classification:
  status: plausible

context:
  primary:
    event: energy_supply_shock
    confidence: high

  secondary:
    event: long_end_term_premium_pressure
    confidence: medium

challenge:
  strongest_support:
    - inflation impulse rising
    - long rates tightening

  strongest_counter:
    - credit remains benign
    - claims remain low

unknowns:
  - durability_of_oil_shock
```

This can later be converted to prose for the user.

---

## 27. Token-Efficiency Rules

Treat these as hard implementation requirements.

### Rule 1

Never send raw historical time series to the agent by default.

### Rule 2

Never send indicators that are neither:

* material drivers;
* contradictions;
* newly changed;
* necessary evidence.

### Rule 3

Cap routine drivers:

```text
max 5
```

### Rule 4

Cap contradictions:

```text
max 3
```

### Rule 5

Prefer compact machine notation over explanatory prose.

### Rule 6

Use cached context instead of re-researching unchanged events.

### Rule 7

Do not invoke the agent if no material macro change occurred.

### Rule 8

Use delta packets for recurring updates.

### Rule 9

Do not ask the agent to perform deterministic calculations.

### Rule 10

Do not send portfolio data unless portfolio interpretation is requested.

---

## 28. Snapshot Versioning

Every deterministic snapshot should include:

```yaml
asof:
model_version:
data_version:
indicator_spec_version:
factor_spec_version:
regime_spec_version:
```

Keep snapshots immutable.

Example:

```yaml
asof: 2026-08-25T00:00:00Z
model_version: 0.1.0
indicator_spec_version: 2
factor_spec_version: 1
regime_spec_version: 1
```

The same version + same point-in-time data must reproduce the same packet.

---

## 29. CLI

Initial commands could conceptually include:

```text
macro-regime update

macro-regime state

macro-regime packet

macro-regime packet --delta

macro-regime evidence

macro-regime should-query-agent

macro-regime agent-prompt

macro-regime snapshot --as-of YYYY-MM-DD
```

Possible routine:

```text
macro-regime update
        ↓
update local data

macro-regime state
        ↓
recalculate factors/regimes

macro-regime should-query-agent
        ↓
true / false

if true:
macro-regime agent-prompt
```

---

## 30. Testing Requirements

Tests should prioritize determinism and token efficiency.

### Data Tests

* correct release cutoff
* no future observations
* revisions handled correctly
* stale data flagged

### Factor Tests

* polarity correct
* missing indicators handled
* contributions sum correctly
* deterministic results

### Regime Tests

* quadrant classification
* affinity boundaries
* state vs impulse separation

### Materiality Tests

Verify insignificant updates do not trigger agent calls.

### Packet Tests

Set hard size budgets.

Example:

```text
routine packet <= 300 tokens
evidence packet <= 1,000 tokens
agent task <= 500 tokens
```

Use an actual tokenizer compatible with the target model if practical.

Add CI tests that fail when packet growth exceeds limits.

---

## 31. Logging and Observability

For each update store:

```text
what data changed
which factors changed
what crossed materiality thresholds
whether an agent call was requested
why it was requested
packet size
cached context reused
```

This allows later measurement of:

```text
agent calls per month
average input tokens
average output tokens
percentage of updates suppressed
```

Token efficiency should be measurable, not assumed.

---

## 32. Recommended Development Phases

### Phase 1 — Data and State

Implement:

* providers
* local store
* indicator specs
* transformations
* state/impulse calculations

Do not add agent integration yet.

### Phase 2 — Factor Engine

Implement:

* Growth
* Inflation
* Rates
* Liquidity
* Stress
* contribution tracking

### Phase 3 — Regime Engine

Implement:

* economic regime
* financial regime
* regime affinity
* regime impulse

### Phase 4 — Diagnostics

Implement:

* driver ranking
* contradiction detection
* confidence
* coverage
* freshness

### Phase 5 — Compact Packet

Implement:

* routine packet
* evidence packet
* delta packet

Enforce token budgets.

### Phase 6 — Materiality Gate

Implement:

* thresholds
* trigger reasons
* suppression of insignificant updates

Measure expected agent-call frequency.

### Phase 7 — Context Cache

Implement:

* event-context storage
* expiry rules
* reuse
* refresh triggers

### Phase 8 — Agent Prompt Generator

Generate concise anomaly-specific prompts.

Do not yet automate agent execution if unnecessary.

Output the prompt for manual ChatGPT use first.

### Phase 9 — Backtesting

Use historical point-in-time snapshots to test:

* regime stability
* signal turnover
* materiality thresholds
* false regime flips
* expected agent call count
* average packet size

Optimize for both analytical usefulness and low token usage.

---

## 33. First Implementation Milestone

The first useful milestone should be:

```text
$ macro-regime packet
```

returning something like:

```yaml
asof: 2026-08-25

econ: stagflationary_slowdown
econ_impulse: deteriorating

financial: restrictive_orderly

G: [-0.31, down, 0.76]
I: [+0.42, up, 0.83]
R: [+0.61, up, 0.91]
L: [+0.18, tighter, 0.69]
S: [+0.09, flat, 0.86]

drivers:
  - WTI +2.1z
  - US30Y +41bp
  - payroll -1.2z

contra:
  - claims benign
  - HY benign
```

And:

```text
$ macro-regime should-query-agent
true
```

followed by:

```text
$ macro-regime agent-prompt
```

producing:

```text
Deterministic macro state:
econ=stagflationary_slowdown
financial=restrictive_orderly

Material changes:
WTI +2.1z
US30Y +41bp/1m
payroll -1.2z

Contradictions:
claims benign
HY benign

Research only:
- cause of oil move
- cause of long-end selloff
- whether credit confirms deterioration

Try to falsify the classification.
Keep the answer concise.
```

If this works well, the architecture is already delivering most of the intended value.

---

## 34. Design Principle to Preserve

The local engine answers:

> **What changed, by how much, and what regime does the deterministic model classify it as?**

The AI agent answers:

> **Why might it have changed, what current events explain it, and what evidence suggests the deterministic model may be wrong?**

Do not let these responsibilities drift.

The desired end state is:

```text
90%+ of routine macro processing:
local / deterministic / zero LLM tokens

LLM usage:
only material anomalies, current context and falsification
```

That is the optimization target.


---

## 35. Plan Assessment

*Added 2026-08-25. Critique of sections 1–34 above.*

The plan is sound in concept and roughly 4x too much machinery for what it does.

### 35.1 What is right

* §34 (division of labor between deterministic engine and agent) — this is the actual idea, and it is a good one.
* §20 (compact packet format) and §24 (targeted anomaly questions instead of "research current macro conditions").
* §19 (materiality gate) — the only component that saves meaningful money.
* §8 (point-in-time) — correct and non-negotiable. Also the hardest part of the project.
* §5 (refusing a single Macro Score) and §14 (refusing to call affinities probabilities). Both disciplined.

### 35.2 Core problem: optimizing the wrong cost

The stated target is minimizing LLM tokens. A 300-token packet versus a 1,000-token packet
is roughly $0.005 per call. If the gate fires 20x/month, that is about a dollar a year.

Sections 21, 22, 27 (ten hard rules) and the CI token-budget tests in §30 exist to defend
a rounding error.

The real cost is **agent web-research invocations** — search plus fetch plus reasoning,
on the order of $0.10–0.50 each. That cost is controlled entirely by §19 (materiality gate)
and §23 (context cache).

Therefore:

```text
load-bearing:  materiality gate, context cache
ceremony:      delta packets, alias scheme, tokenizer CI budgets
```

Delta packets (§22) also cost statelessness: the prompt becomes dependent on what was sent
previously, and a missed send corrupts the next one. That is a real failure mode traded for
a few hundred tokens.

### 35.3 Structural over-build

| Plan | Reality |
|---|---|
| 10 subpackages (§3) | §11–18 is one dataframe pipeline, ~300 lines |
| 9 DuckDB tables (§9) | ~20 series x 10y is ~60k rows; SQLite handles this without noticing |
| Provider abstraction over BLS/BEA/Fed/Treasury/EIA (§7) | FRED already serves nearly every series in §6 |
| 6 version fields (§28) | `git rev-parse HEAD` plus `asof` |
| confidence / coverage / freshness as 3 floats (§17) | coverage and freshness answer the same question; confidence is a dispersion statistic that cannot be calibrated at n=4 |

On providers specifically, FRED covers:

```text
ICSA CCSA PAYEMS UNRATE CPILFESL PCEPILFE
DGS2 DGS10 DGS30 DFII10 T5YIE DTWEXBGS
BAMLH0A0HYM2 BAMLC0A0CM VIXCLS DCOILWTICO
```

That is 16 of the 15–20 target indicators, one API, one key.

**ISM is licensed and not available on FRED.** MOVE and CCC spreads likewise. So the
abstraction layer is being built for sources that mostly cannot be used, while the one
usable source already covers the universe.

### 35.4 Risks the plan understates

1. **ALFRED vintages are the whole project.** §8 is correct, but Phase 1 treats it as one
   bullet among five. Market data has no vintages at all — so Phase 9 backtesting is
   structurally half-blind, and nothing in the plan acknowledges this.

2. **10-year z-scores over a window containing 2020.** Every percentile and standardization
   in §11 is distorted by COVID unless handled explicitly. Not mentioned anywhere.

3. **Weights are guesses presented as structure.** `weight: 0.20` in a YAML spec (§10) looks
   calibrated. It is not. §13 correctly says not to optimize weights, but the driver ranking
   in §18 then inherits that arbitrariness and presents it as importance.

4. **Nine phases before the §33 milestone.** §33 states that reaching it means "the
   architecture is already delivering most of the intended value" — yet it sits behind
   Phases 1–8. That ordering is backwards.

### 35.5 Recommended revision

Build §33 first, directly:

```text
FRED only
one fetch.py, one state.py, one packet.py
parquet files on disk
~10 indicators
```

Target a real packet from real data within a day. Then set gate thresholds from observed
behaviour rather than from config written in advance.

Add back when earned:

```text
DuckDB           when parquet + pandas is measurably slow
provider layer   when a second real provider is added
evidence packet  after a case the compact packet could not answer
delta packets    never
```
