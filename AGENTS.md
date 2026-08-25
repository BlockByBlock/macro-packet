# MacroPacket

## Agent skills

### Issue tracker

Issues are tracked as local markdown files under `.scratch/<feature-slug>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role triage label vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## Macro state packet

Answering any macro question starts at the gate:

    uv run macro-packet update && uv run macro-packet agent-prompt

Exit code 1 means the materiality gate suppressed the call — nothing material
changed since the last snapshot; stop there. Exit code 0 prints a prompt
carrying the state packet (~450 tokens of YAML). Reason over that packet as
the sole engine output, naming factors and regimes per the glossary in
[`CONTEXT.md`](CONTEXT.md).

## Verification

`uv run pytest` runs the full suite offline — seam tests seed a fresh SQLite store, run the pipeline, and assert on its output. No FRED key or network needed. Run it before handing off any change.

## Secrets

This is a public repository. `.env` holds `FRED_APIKEY` and is gitignored; copy
`.env.example` to start. A pre-push hook in `.githooks/` blocks pushing `.env`,
databases, `data/`, and secret-shaped literals. Enable it once per clone:

    git config core.hooksPath .githooks

CI runs gitleaks over full history on every push and PR.
