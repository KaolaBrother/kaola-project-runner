# Finalization Summary — Issue #372

## Delivered

`state retire` now closes the issue shape where an accepted-done task's collected status
had no outcome and its session was already stopped. `stale_collect_session_gone` no longer
requires `status.error_code == "no-session"` (the i241 shape is included) and treats a
stopped live row under the recorded holder as a gone session (strict: every row for that
session must be stopped and name that holder; no row still means absent). Rows whose
collected outcome is `stopped` keep the continuation route.

`collect_status` now records the turn facts already present in the status receipt
(`turn_active`, `turn_outcome`, `stop_reason`), so a collect taken mid-queue is visible
rather than only `outcome: null`. Per the Host ruling, no same-value `receipt_fingerprint`
was added; `prompt_fingerprint` is reused.

`state check`'s `done-not-retired` and `state-bloat` emitters now share
`retire_command_runnable`, which runs the same `open_dispatch` predicate as retire: a
command is printed only when that route would accept it, otherwise `command` is empty and
`detail` names the blocker; without `--index`/`--live` the detail names the missing inputs.
The dead-holder unknown route's reason tuple now includes `session-gone` (#377's collect
branch).

The #354 negative no-session guard was replaced by the positive #372 regression, the new
suite is registered in `validate.sh`, the orchestrator reference documents the route, and
generated Skill copies were refreshed. No tag, release, or install was performed.

## Candidate

Branch `workflow/issue-372` at `6fa04dfd22eaace375d1b475f8d8e263d4e55634`, based on main
`2cb2a715` (the #376 shape guard remains intact). The tip was accepted by the Host after
independent review.

## Evidence

- Host acceptance: verdict `accepted`; independent review 7/7 PASS covering 10 shape
  probes, mutation verification, an independent 217-test rerun, exact baseline-red
  reproduction, and render/#376 guard confirmation.
- `tests/contract/test-issue-372-stale-collect-retire.py` — 13 tests covering the success
  shape, continuation control, live non-stopped and foreign-holder refusals, strict
  mixed-holder, status-less i241, the old no-session guard shape, mid-queue turn facts,
  both check emitters, check without `--index`/`--live`, non-task rows, and the
  session-gone route.
- Focused `./scripts/validate.sh` over 9 suites (217 tests) all OK;
  `render-skills.py --check` PASS; baseline `2cb2a715` shows 9 failures + 1 error for the
  new suite; mutation restoring the old live check turns 5 cases red.
- `kaola-workflow/issue-372/.cache/final-validation.md` records the pass at candidate hash
  `22d68fef60f279b5b575c05023b0c2d7f44116327599b785f9dfb918a0d9a45b`.

## Known failures or unverified scope

- Six non-blocking residues were recorded by independent review. `receipt_fingerprint` was
  intentionally not added (Host ruling; `prompt_fingerprint` is reused). The dead-holder
  reason list in `docs/dispatch-collect.md` and the ddd c4 pack has not yet been updated to
  list `session-gone`, and the reference's every-row wording is pending the same
  documentation sync; these are follow-up documentation items, not blockers, and are noted
  in the issue-closing comment.
- The full inventory gate was not run by this run; focused validation and Host/independent
  review covered the changed paths.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- scripts/kaola-dispatch.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/lifecycle-state.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/references/lifecycle-state.md
- tests/contract/test-issue-354-state-bloat.py
- tests/contract/test-issue-372-stale-collect-retire.py

## Follow-Up Items

- Update `docs/dispatch-collect.md` and the ddd c4 pack dead-holder reason lists to include
  `session-gone`, and align the `state check`/stale-collect reference wording with the
  every-row strictness. No separate issue was filed by this run; the residue is recorded
  here and in the issue-closing comment.

Readiness: accepted candidate at `6fa04dfd`, focused suites and renderer green, ready to
merge, archive, and close.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-372/.cache/final-validation.md
- kaola-workflow/archive/issue-372/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-372/finalization-summary.md
- kaola-workflow/archive/issue-372/mission-ledger.jsonl
- kaola-workflow/archive/issue-372/workflow-state.md
