# MacroPacket

## Agent skills

### Issue tracker

Issues are tracked as local markdown files under `.scratch/<feature-slug>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role triage label vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## Secrets

This is a public repository. `.env` holds `FRED_APIKEY` and is gitignored; copy
`.env.example` to start. A pre-push hook in `.githooks/` blocks pushing `.env`,
databases, `data/`, and secret-shaped literals. Enable it once per clone:

    git config core.hooksPath .githooks

CI runs gitleaks over full history on every push and PR.
