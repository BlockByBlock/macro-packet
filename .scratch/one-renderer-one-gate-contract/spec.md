# Spec: One renderer, one gate contract

Status: ready-for-agent

## Problem Statement

As a maintainer of MacroPacket, two places know too much about things they shouldn't:

1. The CLI's shared gate-evaluation helper hands callers the raw snapshot row
   straight from the store, so two commands each reach into the store's
   serialization format (`previous["as_of"]`) to print a suppression message.
   If the snapshot storage shape changes, CLI code breaks even though its job
   is only printing.
2. Two YAML renderers exist — one for the diagnostic `state` view, one for the
   state packet. They duplicate factor-line and regime-label formatting. A
   wording change must be made twice or the outputs drift apart silently.

## Solution

There is exactly one way to turn macro state into printed YAML (the state
packet renderer), and exactly one place that understands what a stored
snapshot looks like (the materiality module). The CLI shrinks to: build a
packet, ask the gate, print.

## User Stories

1. As a maintainer, I want only one module to know how snapshots are serialized, so that changing snapshot storage never touches printing code.
2. As a maintainer, I want only one YAML renderer for macro state, so that factor and regime wording can never drift between commands.
3. As a maintainer, I want the gate helper to return plain values (packet, previous as-of date, reasons), so that callers cannot depend on store internals by accident.
4. As a maintainer, I want `engine`'s interface to shrink when its renderer moves out, so that callers learn less surface for the same behaviour.
5. As an operator running `macro-packet state`, I want the same compact packet YAML as `macro-packet packet`, so that there is one canonical textual view of current macro state.
6. As an operator running `macro-packet should-query-agent`, I want the same true/false answer and reason list as before, so that my scripts keep working unchanged.
7. As an operator running `macro-packet agent-prompt`, I want the same prompt and the same exit-code-1 suppression behaviour, so that my daily loop keeps gating spend identically.
8. As an operator whose store has never recorded a snapshot, I want the suppression messages to keep saying "(never)", so that first-run behaviour stays readable.
9. As an operator, I want byte-for-byte deterministic output from every command, so that repeated runs at one as-of boundary are diffable.
10. As the AI agent consuming the packet, I want the packet format untouched, so that prompts I already understand stay valid.
11. As a test author, I want to verify both fixes purely through command output and exit codes, so that refactors inside modules don't rewrite tests.
12. As a future contributor adding the evidence packet, I want one renderer to extend rather than two parallel ones, so that the secondary packet inherits consistent wording.
13. As a reviewer of the daily loop (`update` then `agent-prompt`), I want the materiality gate's decision logic untouched by this change, so that cost-control behaviour is provably identical.

## Implementation Decisions

- **Gate helper return narrowed.** The shared CLI gate helper returns
  `(packet, previous_as_of, reasons)` where `previous_as_of` is the plain
  as-of string of the latest prior snapshot (or `None`). Callers never see the
  raw snapshot row; the store-row-to-values conversion happens once, inside
  the helper.
- **Snapshot serialization stays inside materiality.** Loading a stored
  snapshot core from JSON remains the materiality module's job (it already
  owns `evaluate`). No new seam: the JSON contract simply stops leaking past
  the helper into CLI code.
- **One renderer.** `render_state` is deleted. Both the `state` and `packet`
  commands print `render_packet(build_packet(store, as_of))`. The `state`
  command remains a named alias with updated help text; its former extras
  (full affinity distribution, missing-series list) are dropped from output.
- **No behaviour change to the gate.** Thresholds, reason strings, exit codes,
  and the recorded gate log are untouched.
- **No schema changes.** Store interface is unchanged; only who may look at a
  snapshot row narrows.

## Testing Decisions

- Good tests assert external behaviour only: stdout text, stderr, and exit
  codes of CLI commands against a seeded store. No test reaches into helper
  return shapes, snapshot rows, or renderer internals.
- Both fixes are covered through the existing CLI seam — the highest seam in
  the repo. Existing prior art: `tests/test_cli.py`, which already seeds a
  fresh store via the offline conftest fixtures and asserts on command output.
- Required assertions:
  - `should-query-agent` and `agent-prompt` produce identical output before
    and after the change (golden comparison against current behaviour) for:
    material change, no material change, and never-recorded-snapshot cases.
  - `state` and `packet` print identical bytes for the same seeded store and
    as-of boundary.
  - Full suite stays green offline (`uv run pytest`).

## Out of Scope

- Any change to materiality thresholds, reason wording, or gate semantics.
- Any change to the state packet YAML format consumed by the agent.
- Re-adding the dropped diagnostics (full affinity distribution,
  missing-series list) elsewhere — deferred until something consumes them.
- Evidence packet work (already deferred in TODO.md).
- Any provider, store-backend, or schema change.

## Further Notes

- This came out of a deep-module design review; see the codebase-design
  glossary for terms (seam, deep/shallow, interface).
- Deleting `render_state` means `FactorState.missing` data is computed but no
  longer rendered anywhere. That is accepted: the analysis dataclass keeps it,
  and a future diagnostic can re-expose it without reopening this spec.
- The `state` command is kept as an alias rather than deleted so existing
  muscle memory and any scripts referencing it survive.
