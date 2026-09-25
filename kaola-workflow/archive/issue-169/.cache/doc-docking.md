# Doc docking — issue-169

Candidate: `fe480d3` on `workflow/issue-169` (base `2e18946`).
Change: dead-code removal in `scripts/kaola-acp.py` `command_start` (the unreachable
Issue #122 host-entry and Issue #132 host-exists guard blocks), plus the 10 rendered
`skills/*/scripts/kaola-acp.py` copies and the CHANGELOG entry.

## Checked

- `AGENTS.md` — documentation map and constraints. No public behavior changed; the
  generated-surfaces rule (`skills/` re-rendered, never hand-edited) was followed.
- `CHANGELOG.md` — `## Unreleased` carries the #169 entry with an explicit
  `Seats: restart not required` line, justified by the empty operator-test diff.
  Already docked by the implementer; no further change.
- `docs/api.md` — describes the *behavior* of the #122 and #132 refusals
  (`host-entry-unsupported` at lines 368-369; `host-exists` at line 436). Those
  behaviors are unchanged: both refusals still fire on every start path, now solely
  from `pre_spawn_refusal`. No doc text names the removed duplication. No update needed.
- `docs/zcode-host.md` — same: lines 178 and 553 describe refusal behavior that is
  unchanged. No update needed.
- `docs/conventions.md` — the Seats-line rule was read and applied; the operator test
  (`git diff 2e18946 fe480d3 -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py
  scripts/adapters platforms`) is empty, which is exactly the `restart not required` case.
- `README.md` — no command surface, flag, or architecture statement changed. No impact.
- `docs/architecture.md` (if present) — no structural change; one unreachable guard pair
  removed inside an existing function. No impact.

Total changed paths recorded by the finalize check are 12: 1 source file, 10 generated
copies, 1 changelog. None is a documented public surface.

## Not in scope

`docs/api.md` drift-list updates are a separate follow-up issue (outside #169 per the
run authorization).

## Verdict

DOCKED
