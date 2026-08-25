# 06 — Materiality gate + agent prompt

**What to build:** The cost-control core. `macro-packet should-query-agent` compares the current deterministic state against the last recorded one and decides whether anything material happened: regime change, factor state/impulse moves beyond thresholds, indicator shocks beyond ~1.5σ, stress jumps, emerging contradictions. Insignificant updates print a clear negative. When it fires, `macro-packet agent-prompt` prints a targeted prompt containing the deterministic state, material changes, contradictions, and generated research questions aimed at falsifying the classification — per the source plan §24/§33 shapes — for manual pasting into an LLM. Trigger reasons are logged so suppression behaviour is measurable later.

Thresholds start as explicit config placeholders to be tuned from observed behaviour (deferred item in `TODO.md`); no pre-calibration.

**Blocked by:** 04 — Drivers + contradictions.

**Status:** ready-for-agent

- [x] Insignificant update sequence (e.g. growth −0.31 → −0.32) suppresses the agent call
- [x] Material sequence (e.g. WTI shock + inflation jump) triggers it, with reasons recorded
- [x] Generated prompt names only actual anomalies — no generic "research macro conditions"
- [x] Prompt includes the instruction to attempt falsification of the classification
- [x] No automated agent execution anywhere

## Comments

`materiality.py` + `should-query-agent` / `agent-prompt` commands; thresholds are explicit placeholders; reasons recorded in SQLite `gate_log`; snapshots recorded by `packet`; prompt names only actual anomalies and demands falsification; no automated agent execution anywhere.
