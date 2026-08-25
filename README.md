# MacroPacket

A local, deterministic macro engine. It fetches free FRED data into a point-in-time store, computes five macro factors and two regime classifications locally, and emits a **state packet** — ~150–300 tokens of YAML an AI agent can reason over cheaply. A **materiality gate** suppresses agent calls unless something material changed: local software does compression; the agent handles ambiguity.

## Quickstart

```bash
uv sync
echo 'FRED_APIKEY=<your-key>' > .env   # free key: fred.stlouisfed.org/docs/api/api_key.html
uv run macro-packet update             # fetch all 12 series (~150k observations)
uv run pytest
```

`macro-packet --help` lists commands. The store lives at `data/macro.db`.

## Pointers

- **Naming a domain concept** (in code, tests, or issues)? Use the glossary: [`CONTEXT.md`](CONTEXT.md).
- **Touching providers, storage, transforms, or standardization?** Check the binding decisions first: [`docs/adr/`](docs/adr/).
- **Wondering why some obvious machinery is missing** (DuckDB, delta packets, backtesting)? Deferred with re-entry triggers: [`TODO.md`](TODO.md).
- **Picking up implementation work?** The spec and tracer-bullet tickets live under [`.scratch/macro-packet/`](.scratch/macro-packet/).

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
