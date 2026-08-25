# 06 — Materiality gate + agent prompt

**What to build:** The cost-control core. `macro-packet should-query-agent` compares the current deterministic state against the last recorded one and decides whether anything material happened: regime change, factor state/impulse moves beyond thresholds, indicator shocks beyond ~1.5σ, stress jumps, emerging contradictions. Insignificant updates print a clear negative. When it fires, `macro-packet agent-prompt` prints a targeted prompt containing the deterministic state, material changes, contradictions, and generated research questions aimed at falsifying the classification — per the source plan §24/§33 shapes — for manual pasting into an LLM. Trigger reasons are logged so suppression behaviour is measurable later.

Thresholds start as explicit config placeholders to be tuned from observed behaviour (deferred item in `TODO.md`); no pre-calibration.

**Blocked by:** 04 — Drivers + contradictions.

**Status:** ready-for-agent

- [ ] Insignificant update sequence (e.g. growth −0.31 → −0.32) suppresses the agent call
- [ ] Material sequence (e.g. WTI shock + inflation jump) triggers it, with reasons recorded
- [ ] Generated prompt names only actual anomalies — no generic "research macro conditions"
- [ ] Prompt includes the instruction to attempt falsification of the classification
- [ ] No automated agent execution anywhere
