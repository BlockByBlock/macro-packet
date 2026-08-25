# MacroPacket

A local deterministic macro engine that compresses free market/economic data into a compact state packet for an AI agent, invoking the agent only when a materiality gate fires.

## Language

### Packet

**State packet**:
The compact (~150–300 token) YAML summary of current macro state that is the engine's sole deliverable to the AI agent.
_Avoid_: report, digest, briefing

**Driver**:
An indicator whose recent move contributes most to a factor's change; at most 5 appear in a routine state packet.
_Avoid_: important indicator, top signal

**Contradiction**:
An indicator that disagrees with its own factor's direction; at most 3 appear in a state packet.
_Avoid_: anomaly, outlier

**Evidence packet**:
A larger secondary packet (~500–1,000 tokens), generated only on demand. Deferred — see `TODO.md`.

**Materiality gate**:
The local threshold test that decides whether a data change justifies an agent invocation. No material change means no agent call.
_Avoid_: trigger system, alerting

**Context cache**:
Local store of previously researched event context, reused instead of re-researching unchanged events.

### Factor engine

**Factor**:
One of five standardized macro dimensions: Growth, Inflation, Rates Pressure, Liquidity Pressure, Financial Stress.
_Avoid_: pillar, score, index

**State**:
A factor's current underlying condition (a single signed number).
_Avoid_: level, value

**Impulse**:
A factor's recent rate of change — distinct from and always reported alongside its state.
_Avoid_: trend, momentum

**Contribution**:
An indicator's clamped z-score at the as-of boundary, multiplied by its weight; contributions sum to the factor's state.
_Avoid_: score, signal

**Economic regime**:
The quadrant of the Growth × Inflation plane (e.g. stagflationary slowdown).

**Financial regime**:
The descriptive combination of rates, liquidity, and stress states (e.g. restrictive orderly).

**Affinity**:
Continuous membership strength in an economic regime, computed as softmax over distances from regime centers in the Growth × Inflation plane. Sums to 1 across regimes.
_Avoid_: probability, confidence, likelihood

### Data

**Vintage**:
A release-timestamped version of an observation: the first date a value was knowable. Stored append-only so any past moment can be replayed.
_Avoid_: revision history, snapshot

**As-of boundary**:
The explicit timestamp every calculation must accept; `latest` never exists without one.

