# Finalization Summary — issue #160

## Delivered

`install-local.sh` no longer leaves an **owned** `kaola-delegator` leftover stale under a Host
root that must not install it (`--runtime zcode`, `claude-code`, and the other `*_no_external`
Host roots). Policy chosen: **refresh-if-present, owner-preserving** — on a Host-runtime
reinstall the owned leftover's **content** is refreshed to the accepted build via a new
`plan_skill` `preserve=1` path that never registers the Host runtime as a referrer, so
referrers stay exactly as recorded (e.g. `[generic]`), the documented remediation
`--skills-dir ~/.zcode/skills --uninstall` still removes the copy, and zcode alone can never
keep it alive. A foreign unowned tree or a foreign/broken symlink under a Host root is refused
before any write; a same-build reinstall is a no-op; `--no-orchestrator` skips this planning
entirely. The fresh-install `no_external` default is unchanged (a fresh `--runtime zcode`
never creates the Delegator).

Implementation commit (frozen, reviewed): `3af5dba138355e336528b4422bebeb30535682d1`.

## Files Changed

- `scripts/install-local.sh` (+62/−14 net in candidate): `plan_skill` gains `preserve=1`
  (owner-preserving refresh; all referrer mutations routed through `refs_with_owner`),
  Host-runtime Delegator planning calls `plan_skill "$external_skill_name" "" 1`, usage text
  documents refresh-if-present, owner preservation, symlink refusal, `--no-orchestrator` skip.
- `tests/contract/test-installer-runtimes.sh` (+163): refresh/ledger/noop/kept/removed
  pins, issue-exact-state zcode-uninstall-without-refresh, generic-removal-after-refresh,
  foreign tree + foreign/broken symlink refusals, `--no-orchestrator` untouched, claude-code
  generalization; existing `test_runtime_zcode_no_external` / `test_runtime_claude_code_no_external`
  defaults still pinned and passing.
- `README.md` (+9): installer usage paragraph updated to owner-preserving wording.
- `docs/zcode-host.md` (+12): pin-refresh section documents owned-leftover refresh without
  ZCode ownership, remediation, refusals, `--no-orchestrator`.
- `CHANGELOG.md` (+20/−2): Unreleased Issue #160 bullet matching the implemented behavior.

Run-state only (not part of the candidate): `kaola-workflow/issue-160/` (workflow-state,
doc-docking, final-validation) and `kaola-workflow/.ledger/issue-160.jsonl`.

## Test Coverage

- `tests/contract/test-installer-runtimes.sh` — PASS (includes the new Issue #160 block).
- `tests/contract/test-installer-migration.sh` — PASS.
- `tests/contract/test-issue-123-shared-refs.py` — 6/6 tests, 62 checks PASS.
- Live zcode dry-run smoke (`/tmp/kpr-i160-smoke2.7mvpnd`) — 7/7 PASS: fresh no_external
  default, seed old build, refresh updates SHA to accepted with referrers staying `[generic]`,
  same-build no-op, generic `--skills-dir --uninstall` removes after refresh, zcode
  `--uninstall` without prior refresh keeps the copy, fresh fixed install still no Delegator.
- Full `./scripts/validate.sh` — exit 0 (final receipt below under ## Validation).

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- README.md
- docs/zcode-host.md
- scripts/install-local.sh
- tests/contract/test-installer-runtimes.sh

## Documentation Docking

DOCKED — see `.cache/doc-docking.md`. README, CHANGELOG, docs/zcode-host.md, and the installer
usage/help text were updated in the candidate; every doc claim is pinned by a contract test or
the live smoke (mapping recorded in the docking evidence).

## Follow-Up Items

None filed. Review round 1 (Claude Code) found one blocker — owner registration — fixed by the
repair; review round 2 recorded three non-blocking minors with an explicit "do NOT fix now"
directive (link-method contract rows, pre-#123 default-owner edge note, uninstall-refusal doc
line). No run-discovered defects needing new issues; no keep-open decision (issue_action close).
Duplicate probe: `searched: gh issue view 160` — 1 hit (this issue), no duplicate.

## Final Readiness Status

READY — candidate frozen, validation pass recorded, acceptance granted (review round 2 VERDICT
PASS), docs docked, archive and merge-sink pending in this finalization transaction.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-160/.cache/doc-docking.md
- kaola-workflow/archive/issue-160/.cache/final-validation.md
- kaola-workflow/archive/issue-160/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-160/finalization-summary.md
- kaola-workflow/archive/issue-160/mission-ledger.jsonl
- kaola-workflow/archive/issue-160/workflow-state.md
