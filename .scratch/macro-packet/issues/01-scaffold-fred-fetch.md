# 01 — Scaffold + FRED fetch into point-in-time store

**What to build:** A working `uv`-managed Python project (package `macro_packet`, CLI `macro-packet`, stdlib argparse) whose first command, `macro-packet update`, fetches all twelve v1 indicators from FRED and stores every observation append-only with its release timestamp in a single SQLite file. Running it twice must never duplicate or overwrite rows — only append new vintages. The FRED API key is read from `.env` (gitignored).

Series: ICSA, PAYEMS, UNRATE, CPILFESL, T5YIE, DCOILWTICO, DGS2, DGS10, DFII10, DTWEXBGS, NFCI, VIXCLS.

Respect: FRED-only providers (ADR-0001), append-only vintage store from day one using the regular FRED endpoint's vintage parameters (ADR-0002).

**Blocked by:** None — can start immediately.

**Status:** done (slice 1 shipped)

- [x] `macro-packet update` populates the SQLite store with all 12 series
- [x] Economic series rows carry release timestamps from FRED vintage parameters; re-running appends without duplication
- [x] Store schema distinguishes observation period, release timestamp, value, source, ingestion time
- [x] `.env` key loading works; no key material in git
