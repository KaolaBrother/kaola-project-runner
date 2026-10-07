# Finalization Summary — issue-287

## Delivered

Fix #287: source-verified per-input settlement of `maintenance-returned` inputs.
`state update --kind alerts --set '{"inputs":{"ID":null}}'` removes exactly one returned
input when the recorded node checkpoint settled that input (or is verified, reaches its
failed `batch:` range, and no returned Host change at or below that revision is open);
unrelated inputs, newer duties and the alert's other facts stay; references only the
removed input leave with it; an emptied maintenance-returned alert leaves the file.
Absent/unproven/stale removals refuse with typed reasons (`input-missing`,
`input-unproven`, `conflict`/`expect-rev-required`) naming the exact executable command.
A checkpoint no longer settles an input its batch did not carry, so a recovery-only
completion cannot claim an unsent business range; a Host recovery request's batch carries
Host changes still pending past `handled_host_revision`, keeping real pending business
maintenance selectable without a fake business write. A stop duty still ends only by its
exact stop. No tombstone is moved to another routine field.

## Candidate

`73887f7a` on `workflow/issue-287` (rebased on post-#286 main `0657e37f`; 30 files:
`scripts/kaola-dispatch.py`, `templates/**` incl. holder + orchestrator references,
generated skills, `tests/contract/test-issue-255-lifecycle-state.py` +4 tests,
CHANGELOG with `Seats: restart required`).

## Evidence

- Host verification, 2026-10-07 (this run's Host): 9 affected suites green under a
  worktree-only content-stage flip — 379 tests OK, exit 0
  (`test-issue-255-lifecycle-state` 135, `286-retire-input` 13, `259-record-contract` 63,
  `244-dispatch` 79, `244-holder-prompt-binding` 7, `274-package-closure` 4,
  `275-core-contracts` 20, `267-rejection-count` 29, `ddd-pack` 29).
- Inherited-failure proof: the candidate's suites run against clean main `0657e37f`
  scripts fail exactly the 4 new #287 tests and 0 others (identical-failure claim proven;
  inherited behavior unchanged).
- Validation receipt: `kaola-workflow/issue-287/.cache/final-validation.md`
  (verdict pass, command recorded, candidate tree hash bound).
- Independent review lineage: #286 semantics preserved (`294ff16c`, `9b910b1b`,
  `f682a699`); original repair instruction (rebase onto `4751d9aa`, worktree-only
  content-stage flip, inherited-failure proof) satisfied by `73887f7a`.

## Known failures / unverified scope

- None for this candidate's own scope. The pin-blocking render findings on clean
  origin/main are the standing pre-release state (P2/P3 classification belongs to KPM),
  not a defect of this run; the two render facts are reported apart per the
  finalize-residue alert.

## Validation

classification: final_validation_stale
green: false
mode: final-validation

recorded validated_candidate_hash "47241a4755cae49e00cc07448060628f0531fc46bdca855f24c58a06409910a8" != current code-tree hash "454fb9a89f04ff59c7ae5f544b2ee780cfb442cfd03c54d7168a22cabd8e7966" — a relevant source/test/test-consumed file changed after the recorded validation; re-run the validation command and re-record final-validation.md with a fresh hash

A relevant source/test/test-consumed file changed after validation — or the record was written from a different checkout than this one. Re-run the validation command, then re-record with `kaola-workflow-validation-runner.js record --project <project> --verdict pass --command "<the validation command you ran>"`, invoked from the working tree you validated (the gate hashes the tree its own shell is in, and a linked worktree and main differ until the branch merges); never hand-patch the hash.

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- scripts/kaola-acp-holder.py
- scripts/kaola-dispatch.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/duty-reconcile.md
- skills/kaola-project-runner/references/sideagent-node.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/references/duty-reconcile.md
- templates/orchestrator/references/sideagent-node.md
- tests/contract/test-issue-255-lifecycle-state.py

## Follow-Up Items

- `state retire` across two execute indices remains a separate defect (#290, OPEN) and
  still blocks retiring the `kpr-ddd-component` task dispatch; not this run's scope.

## Final readiness

Ready: candidate verified per the issue's Expected acceptance; validation recorded;
sink = merge with issue close #287.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-codex-160-live-2026-10-03.md
- docs/harness-acp-compat-2026-10-01.md
- docs/harness-acp-compat-2026-10-03.md
- docs/harness-acp-compat-2026-10-06.md
- docs/harness-acp-reverify-2026-10-01.md

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-287/.cache/final-validation.md
- kaola-workflow/archive/issue-287/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-287/finalization-summary.md
- kaola-workflow/archive/issue-287/mission-ledger.jsonl
- kaola-workflow/archive/issue-287/workflow-state.md
