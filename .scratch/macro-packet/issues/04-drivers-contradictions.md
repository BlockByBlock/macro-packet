# 04 — Drivers + contradictions

**What to build:** Local ranking of what matters. Drivers: the top indicators behind recent factor movement, ranked by absolute standardized shock × factor weight, capped at 5. Contradictions: indicators disagreeing with their own factor's direction, strongest conflicts only, capped at 3. Both derivable entirely from already-stored contributions and specs — no new data.

Respect: glossary definitions of driver and contradiction including their caps; weights remain hand-set guesses (deferred calibration, `TODO.md`) so importance inherits that arbitrariness by design.

**Blocked by:** 02 — Indicator specs → five factor states.

**Status:** ready-for-agent

- [x] Driver list capped at 5, ranked by the documented formula
- [x] Contradiction list capped at 3, showing genuine cross-signal disagreement (e.g. growth down but claims benign)
- [x] Both computable at an arbitrary as-of boundary
- [x] Insignificant days can yield empty driver lists rather than noise

## Comments

`diagnostics.py`: drivers capped at 5 ranked by |standardized shock| x hand-set weight; contradictions capped at 3 strongest cross-signal conflicts; both accept an arbitrary as-of boundary; quiet stores yield empty lists.
