# Doc docking — issue-174

Candidate: `dbc6f21` on `workflow/issue-174` (base `0c3d200`).
Change: three observation-ordering fixes in `scripts/kaola-acp-holder.py`
(the `stdin_write_failed` connection fact + `initialize_agent` write-failure
classification; `on_agent_exit` verdict-state preservation and in-place
still-pending slot resolution; `start_failure_facts` exit-ordered stderr
drain under `EXIT_GRACE`), plus the 10 rendered
`skills/*/scripts/kaola-acp-holder.py` copies and the CHANGELOG entry.

## Checked

- `AGENTS.md` — documentation map and constraints. Generated-surface rule
  followed: `skills/` re-rendered via `./scripts/render-skills.py --write`,
  verified byte-identical by `--check` (PASS); never hand-edited.
- `CHANGELOG.md` — `## Unreleased` carries the #174 entry. It states
  **`Seats: restart required.`** Verified against the operator test myself:
  `git diff 0c3d200 dbc6f21 -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/adapters platforms`
  is non-empty (`scripts/kaola-acp-holder.py` changed), which is exactly the
  restart-required case per `docs/conventions.md` and the AGENTS.md release
  rule. Already docked by the implementer; no further change.
- `docs/conventions.md` — the Seats-line rule was read and applied; the
  entry names the operator test and its non-empty result explicitly.
- `docs/api.md`, `docs/architecture.md` — no public API, flag, command, or
  architecture surface changed. The receipt vocabulary is unchanged (the
  same error codes and fields are produced, deterministically now): the
  state set still contains all six documented states (`agent_exited` remains
  the post-boot exit state), `stderr_tail` / `seatbelt_confined` keep their
  Issue #120 shapes. No update needed.
- `docs/poc-acp-transport-2026-09-11.md`, `docs/acp-live-verification-2026-09-11.md`,
  `docs/runner-v2-dual-transport-design-2026-09-11.md` — dated historical
  evidence records of measured runs; they describe the receipt shape
  (`error: {code, message, stderr_tail: [...]}`) and outcomes that are
  unchanged by this fix. Historical evidence is not rewritten.
- `README.md` — no command surface, flag, or architecture statement
  changed. No impact.

Total changed paths outside run state: 12 (1 holder source, 10 rendered
copies, 1 CHANGELOG). None is a documented public surface beyond the
CHANGELOG entry itself.

## Not in scope

No run-discovered defect outside #174's own races was found (the
mid-validation discovery that mock suites pin `pending_out` membership
admission was a constraint of the fix's design, respected in the final
shape, not a product defect). No follow-up to file.

## Verdict

DOCKED
