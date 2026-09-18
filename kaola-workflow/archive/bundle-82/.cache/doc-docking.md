# Documentation Docking — bundle-82

verdict: DOCKED

Changed public behavior: none in production code. The diff touches only
`tests/contract/test-acp-contract.py` and `tests/contract/test-acp-watch-contract.py`
— fixture teardown now stops the platform it started, the socket-replaced watch
holder is reclaimed via the existing `kaola-acp-sweep.py` bounded to that test's
own record dir, and per-class assertions prove zero own holders/mock agents
survive a standalone run. No Runner lifecycle, Skill surface, script interface,
or generated output changed.

Checked files:

- `README.md` — documents `./scripts/render-skills.py --check` and
  `./scripts/validate.sh` as commands; no fixture-teardown prose. No impact.
- `docs/conventions.md` — mentions validate.sh only as the after-change
  command. No impact.
- `docs/architecture.md`, `docs/api.md` — no standalone-test-fixture behavior
  described. No impact.
- `docs/runner-v2-dual-transport-design.md` — historical design doc. No impact.
- `AGENTS.md` — Commands/Validation Policy name validate.sh/render only; no
  behavior detail to update. No impact.
- `CHANGELOG.md` — house convention records every issue's fix under
  `## Unreleased` (Issue #80's test-only fix has an entry). FIX APPLIED: entry
  added describing the wrong-platform teardown, the socket-replacement leak,
  the exact-record-dir sweep reclaim, and the own-process assertions.
- `tests/contract/test-issue-49-grok-bot-host.py` stale-string sweep covers
  CHANGELOG.md — new entry introduces none of its forbidden strings (verified
  by that suite's pass in the plain full validate at b158e16 base state; the
  delta itself contains none).

Evidence: `kaola-workflow/bundle-82/evidence/` — focused-test-*-88042cd.log,
standalone-test-acp-*-88042cd.log, validate-plain-88042cd.log,
render-check-88042cd.log, diff-b158e16.patch, ps snapshots.
