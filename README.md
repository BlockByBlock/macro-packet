# MacroPacket

A local, deterministic macro engine. It fetches free FRED data into a point-in-time store, computes five macro factors and two regime classifications locally, and emits a **state packet** — ~100–150 tokens of YAML an AI agent can reason over cheaply. A **materiality gate** suppresses agent calls unless something material changed: local software does compression; the agent handles ambiguity.

## Quickstart (once per clone)

```bash
uv sync
echo 'FRED_APIKEY=<your-key>' > .env   # free key: fred.stlouisfed.org/docs/api/api_key.html
uv run macro-packet update             # fetch all 12 series (~150k observations)
uv run pytest                         # offline: synthetic data, no API key needed
```

Daily use is two commands:

```bash
uv run macro-packet update   # refresh data
uv run macro-packet packet   # print the state packet (--as-of defaults to today)
```

## Agent usage

Agents call one command; the **materiality gate** decides everything else:

```bash
uv run macro-packet update && uv run macro-packet agent-prompt
```

- Exit 1 — no material change since the last snapshot. Stop; spend no tokens.
- Exit 0 — the gate fired. The output is a ready-made prompt carrying the
  state packet (~100–150 tokens); reason over it and answer its questions.

Sample (first run — no prior snapshot):

```yaml
Deterministic macro state:
asof=2026-08-25
econ=reflation (affinity 1.00, improving)
financial=restrictive_orderly

Material changes:
no previous snapshot recorded

Research only:
- What drove the fall in DTWEXBGS?
- What drove the rise in ICSA?
...
Try to falsify the classification.
Keep the answer concise.
Write the answer in Simplified Technical English: active voice,
short sentences (max 20 words), one idea per sentence.
```

## Pointers

- **Naming a domain concept** (in code, tests, or issues)? Use the glossary: [`CONTEXT.md`](CONTEXT.md).
- **Touching providers, storage, transforms, or standardization?** Check the binding decisions first: [`docs/adr/`](docs/adr/).
- **Wondering why some obvious machinery is missing** (DuckDB, delta packets, backtesting)? Deferred with re-entry triggers: [`TODO.md`](TODO.md).
- **Filing or picking up work?** The tracker lives under [`.scratch/`](.scratch/) — one `<feature-slug>/` directory per feature: spec plus one file per ticket.

## Layout

```
src/macro_packet/   engine package (store, fred fetcher, CLI)
tests/              seam tests: seed SQLite → pipeline → assert output
data/               local SQLite store (gitignored)
.scratch/           issue tracker: spec + one file per ticket
docs/adr/           architecture decisions
CONTEXT.md          domain glossary
TODO.md             deferred work with re-entry triggers
```
