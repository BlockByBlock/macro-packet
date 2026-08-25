# 05 — The state packet

**What to build:** The product itself: `macro-packet packet` assembles factors (state, impulse direction, confidence), both regimes with primary affinity, drivers, contradictions, and market confirmation lines into compact YAML targeting ~150–300 tokens, matching the shape of the source plan's §33 milestone. Compact aliases (G/I/R/L/S) defined once in output convention. Output must be byte-for-byte deterministic given the same store and code.

This is the acceptance gate for the whole slice-1 effort: if this command's output is trustworthy, the architecture is delivering its value.

**Blocked by:** 03 — Economic + financial regimes; 04 — Drivers + contradictions.

**Status:** ready-for-agent

- [x] Packet matches the §33 target shape (asof, econ, financial, G/I/R/L/S lines, drivers, contra)
- [x] Routine packet stays within ~300 tokens on real data (rough token estimate, not tokenizer CI)
- [x] Byte-determinism test green across repeated runs
- [x] Empty driver/contra sections render cleanly rather than being omitted silently

## Comments

`packet.py` + `macro-packet packet` (§33 shape, compact G/I/R/L/S aliases, confirm line, empty sections render as `[]`, byte-determinism test, rough token-budget test).
