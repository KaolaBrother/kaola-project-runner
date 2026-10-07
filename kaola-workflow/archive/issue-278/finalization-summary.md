# Issue #278 finalization summary

## Delivered

ACP record discovery no longer follows caller TMPDIR: stable per-UID root,
bounded legacy-root discovery, cross-root Host uniqueness, applied socket-path
persistence, and typed mismatch refusal. Runner/holder verify caller ownership
and directory type, create/tighten private 0700 directories with no-follow
verified descriptors, and refuse unsafe write roots before start/holder writes
or drain-restart stop. Legacy readers remain read-only. Worker copies are
canonical renderer products; docs and Unreleased restart requirement are updated.

## Acceptance

Host **ACCEPTED** `86c873e373eac7f580ff0be252bf7899032c52f0`. Rebased onto current origin/main
`4c30b71d0b964628c5a39159ff0cd89504adcd6b` without conflicts; runtime candidate
`b81f2734ee944964b5f173eac2961d08eb277cf7` has identical scripts/skills/tests bytes to the accepted candidate.
Owner authorized finalize/merge/push, conditional on an exact pre-push allowed
path check, and required `issue_action: comment_keep_open` for issue #278.

## Evidence

`docs/issue-278-validation.md` records exact commands, source/log digests and
coverage. Accepted final four suites PASS (95.1004 s): root 10 tests, list
identity 9 tests, ACP 85 tests, generated Skill acceptance. Post-rebase selected
root suite in the fresh QA clone PASS (10 tests, 8.263 s; validation 9.22137 s),
with no residual fixture processes. Unchanged earlier scope evidence is reused.

## Known limits and publication boundary

Original renderer write/check still exit 1 at inherited protected v0.9.1 pin
delta; owner accepted this boundary. Disposable content-stage QA render/check
and canonical worker byte inventories pass; no release/saveable pin or native
paid platform integration/installation is claimed. Existing legacy roots are
not permission-migrated by readers. Seats: restart required.

Installed finalize has a main-to-worktree residue mirror. The pre-push check
must stop on any protected or unexpected path, including the four dirty Grok
Bot/pin files in main. Never stage/modify/delete these protected paths in the
main checkout. Local archival is not publication evidence.

## Validation

classification: final_validation_stale
green: false
mode: final-validation

recorded validated_candidate_hash "c9854753b28057a72904a58175b332579eb5de463dc63c769d2d82288a6906a0" != current code-tree hash "a3c6bedaa7a5596624c03c8e98854c4de6b7bd0d8aa63b4848927672d4158cec" — a relevant source/test/test-consumed file changed after the recorded validation; re-run the validation command and re-record final-validation.md with a fresh hash

A relevant source/test/test-consumed file changed after validation — or the record was written from a different checkout than this one. Re-run the validation command, then re-record with `kaola-workflow-validation-runner.js record --project <project> --verdict pass --command "<the validation command you ran>"`, invoked from the working tree you validated (the gate hashes the tree its own shell is in, and a linked worktree and main differ until the branch merges); never hand-patch the hash.

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- docs/architecture.md
- docs/conventions.md
- docs/grok-bot-host.md
- docs/issue-278-validation.md
- docs/poc-acp-transport-2026-09-11.md
- docs/runner-v2-dual-transport-design-2026-09-11.md
- scripts/kaola-acp-holder.py
- scripts/kaola-acp-paths.py
- scripts/kaola-acp-sweep.py
- scripts/kaola-acp.py
- scripts/kaola-launchd-broker.py
- scripts/kaola-locate.py
- scripts/render-skills.py
- scripts/validate.sh
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-paths.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp-paths.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-paths.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp-paths.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp-paths.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp-paths.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp-paths.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-paths.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp-paths.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp-paths.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-launchd-broker.py
- tests/contract/test-acp-contract.py
- tests/contract/test-acp-follow-contract.py
- tests/contract/test-acp-sweep-contract.py
- tests/contract/test-acp-watch-contract.py
- tests/contract/test-issue-255-lifecycle-state.py
- tests/contract/test-issue-266-launch-broker.py
- tests/contract/test-issue-278-record-root.py
- tests/contract/test-issue-33-config-meta.py
- tests/contract/test-issue-49-grok-bot-host.py
- tests/contract/test-issue-65-steering.py
- tests/contract/test-issue-76-permission-wake.py
- tests/contract/test-issue-92-permission-wake-recovery.py
- tests/contract/test-zcode-heartbeat-contract.py

## Follow-Up Items

Keep #278 open: release/install acceptance remains pending (root gate). After
verified push only, comment with merge commit and validation summary:
"merged to main at <merge commit>, pending release/install (root gate); Seats: restart required".
No new follow-up issue or backlog reorganization is required for this scope.

## Readiness

Implementation ACCEPTED; local finalization may proceed. Publication requires
the owner's hard path boundary to pass. Release/install remain pending.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-codex-160-live-2026-10-03.md
- docs/harness-acp-compat-2026-10-01.md
- docs/harness-acp-compat-2026-10-03.md
- docs/harness-acp-compat-2026-10-06.md
- docs/harness-acp-reverify-2026-10-01.md

