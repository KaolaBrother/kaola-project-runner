# Finalization Summary — Issue #258

## Delivered

Accepted candidate: 607dc0963d7b7b2cb6f3795ec718d1aac9bb46b8 (branch workflow/issue-258, base
main 162fbe7a). The Host accepted this exact commit.

In tests/contract/test-issue-162-upgrade-safety.py,
`UpgradeSafetyTests.test_release_note_rule_and_no_rebind_wording` no longer requires a standing
`## Unreleased` heading in CHANGELOG.md. It now checks the documented release-note rule
(docs/conventions.md "Release labels and running seats", AGENTS.md) on the current release
section: the first `## ` section of CHANGELOG.md must contain a line that is exactly
`Seats: restart required` or `Seats: restart not required`. The existing
`**Seats: restart required.**` assertion is unchanged. An in-memory negative check (the 0.9.0
Seats line removed) makes the new check fail.

No `## Unreleased` heading or release section was added. CHANGELOG.md, docs/conventions.md and
AGENTS.md are unchanged by this branch. Doc impact: none. No release, tag, publish or install.

Evidence (matches the candidate's bytes): /tmp/kpr-i258-seats-delivery.md,
/tmp/kpr-i258-validate.log. With FORCE_COLOR/CLICOLOR_FORCE unset and NO_COLOR=1 CLICOLOR=0:
the focused test exited 0 and `./scripts/validate.sh` exited 0 from the worktree.

## Known failures or unverified scope

- Live per-platform ACP smoke tests were not run; this change touches only a contract test.
- The main checkout carries an uncommitted AGENTS.md paragraph (owner clarification for #259)
  that is not part of this run and is left out of it.

## Validation

classification: final_validation_stale
green: false
mode: final-validation

recorded validated_candidate_hash "a316e8b3d40f9244a88b7047d43b315d51e13b1cd5af4ed697e4a022ca6973ed" != current code-tree hash "ad5fdf542aa124f28dd83c34aec797b901e1a15fa8141ce5767ca2bc653ec2a0" — a relevant source/test/test-consumed file changed after the recorded validation; re-run the validation command and re-record final-validation.md with a fresh hash

A relevant source/test/test-consumed file changed after validation — or the record was written from a different checkout than this one. Re-run the validation command, then re-record with `kaola-workflow-validation-runner.js record --project <project> --verdict pass --command "<the validation command you ran>"`, invoked from the working tree you validated (the gate hashes the tree its own shell is in, and a linked worktree and main differ until the branch merges); never hand-patch the hash.

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- tests/contract/test-issue-162-upgrade-safety.py

## Follow-Up Items

- None filed. Observation: the claim script reported "gh issue fetch transient fault" twice
  until FORCE_COLOR/CLICOLOR_FORCE were unset; colorized `gh` JSON output is the likely cause
  (hypothesis, not confirmed).

## Finalize Findings

### mirrored_unrelated_edit

The finalize transaction mirrored the main checkout's uncommitted AGENTS.md paragraph (#259
owner clarification, not part of this run) into `chore: finalize issue-258` (e8f62336). That
changed the code-tree hash and produced the `final_validation_stale` finding above. Commit
34c3fda3 restores AGENTS.md to its base content without rewriting history; the branch's net
diff against 162fbe7a is again only tests/contract/test-issue-162-upgrade-safety.py, and the
tree is byte-identical to the validated candidate 607dc096. The paragraph remains uncommitted
in the main checkout.

## Readiness

Ready for archive and merge sink. Closure decision: close #258 on the verified merge.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-codex-160-live-2026-10-03.md
- docs/harness-acp-compat-2026-10-01.md
- docs/harness-acp-compat-2026-10-03.md
- docs/harness-acp-reverify-2026-10-01.md

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-258/.cache/final-validation.md
- kaola-workflow/archive/issue-258/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-258/finalization-summary.md
- kaola-workflow/archive/issue-258/mission-ledger.jsonl
- kaola-workflow/archive/issue-258/workflow-state.md
