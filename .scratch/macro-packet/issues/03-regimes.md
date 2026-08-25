# 03 — Economic + financial regimes

**What to build:** Classification on top of the factors. Economic regime: softmax affinities over quadrant centers in the Growth × Inflation plane (Goldilocks, Reflation, Disinflationary Slowdown, Stagflationary Slowdown), yielding a primary label plus a continuous affinity map — never hard boundaries, never called probabilities. Financial regime: descriptive combination of rates, liquidity, and stress states (e.g. restrictive orderly). Regime impulse (deteriorating/improving) from affinity movement.

Respect: glossary definitions of economic regime, financial regime, and affinity; the temperature constant for the softmax gets pinned by tests here.

**Blocked by:** 02 — Indicator specs → five factor states.

**Status:** ready-for-agent

- [x] Quadrant classification matches expected labels at clear-cut factor readings
- [x] Affinities are continuous: near a quadrant border, two regimes have comparable affinity
- [x] Primary label is the affinity argmax; affinities sum to 1
- [x] Financial regime combines rates/liquidity/stress into a descriptive state
- [x] Regime output appears alongside factors in `macro-packet state`

## Comments

`regimes.py`: softmax affinities over quadrant centers, temperature pinned by tests (`tests/test_regimes.py`); financial regime descriptive combination; regime output in `state`.
