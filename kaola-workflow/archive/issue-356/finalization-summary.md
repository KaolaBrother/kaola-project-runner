# Finalization Summary — issue-356

## Delivered

Issue #356 (bookkeeping 1B): the bound Sideagent node retires a task that the Host accepted, under strict conditions, inside its reconcile batch.

- The node prompt is in `scripts/kaola-acp-holder.py` `_node_prompt`, not in a template. The old role limit did not forbid task retirement, but no instruction told the node to retire a task. The prompt now states the rule: six conditions, `--expect-rev` read at retire time, `conflict` re-read and retry once, then `applied: ["retired:tasks/<id>"]`. After any other refusal, or a second conflict, the node retires nothing and records `returned`.
- `scripts/kaola-dispatch.py` `retire_record` adds three refusals (`retire-unmet`), only for a Sideagent writer that retires a task: `wait` is not blank, `keep_open` is true, or a pending decision or a current alert references the task. Each refusal carries a `recovery` hint. The existing checks are not relaxed. Host retire is unchanged.
- Checkpoint has a third verb, `returned`. The node's reason lands verbatim in `returned_to_host` and in `maintenance-returned`, and the standing Host-owned rule never settles it.
- No new stored field, no stone, no Host-only section write. A Sideagent retire does not raise `host_revision`.
- Rebased onto `2e5b6f52` after #355 and #357. `scripts/kaola-dispatch.py` merged automatically. `CHANGELOG.md` keeps the #353, #354, #355, and #357 Unreleased bullets and appends #356. The section line stays `Seats: restart required`. The generated `main-skill-build.json` files were regenerated with `./scripts/render-skills.py --write`.

## Candidate

Branch `workflow/issue-356`, parent `2e5b6f529a5208007acf379f68991eb31f9abc47`.

- `e7223fc2` — `Let the Sideagent retire a Host-accepted task under strict conditions (#356)`

Acceptance candidate: `e7223fc2`. The worktree is clean. This finalize adds no implementation commit.

Host acceptance: ACCEPTED. The acceptance of `75d3dd7f` still covers this candidate because the diff is the same line for line (`scripts/kaola-dispatch.py` +61, `scripts/kaola-acp-holder.py` +18/−2).

The operator diff of `2e5b6f52..e7223fc2` (`scripts/kaola-acp-holder.py`, `scripts/kaola-zcode-acp.py`, `scripts/kaola-quota.py`, `scripts/kaola-record-contract.py`, `scripts/adapters`, `platforms`, `scripts/kaola-acp-paths.py`) touches only `scripts/kaola-acp-holder.py`, which holds the node prompt. Thus this change also needs `Seats: restart required`.

## Evidence

- Fail-on-main, on `7e255f0b` with only the new test file: `Ran 14 tests` / `FAILED (failures=13, errors=1)`. After the change: `Ran 14 tests` / `OK`.
- One counterexample per condition, in `SideagentTaskRetire`. The retire is refused, the state file bytes do not change, and the `returned` reason is in `returned_to_host`: (1) a verdict that is not final; (2) an in-flight dispatch row (a `--handoff` still retires); (3) no cite, or a cite to a missing file; (4) `transcribed`; (5) `wait`, `keep_open`, a pending decision reference, or an alert reference (a settled decision does not block); (6) a live session.
- Concurrency: a stale rev gives exit 3 `conflict` and the file does not change. A re-read and retry succeeds. A second conflict is returned to the Host and is not forced.
- 12-round stability: rounds 0–10 are verified, with no accepted-and-done task left and the standing task, decision, authorization, and in-flight index row byte-equal. Round 5 has an injected conflict that the retry repairs. Round 11 has two conflicts and is returned to the Host.
- Restore: the retire result carries kind, id, outcome, cite, and writer_holder. The index row keeps `task_id` and the mirrored `acceptance: accepted` with `acceptance_source`.
- Focused suites after the rebase, on `e7223fc2`: `test-issue-255-lifecycle-state.py` Ran 156 tests OK; `test-issue-349-checkpoint-verb.py` Ran 39 tests OK; `test-issue-348-backstop-sweep.py` Ran 33 tests OK; `test-issue-354-state-bloat.py` Ran 12 tests OK. `./scripts/render-skills.py --check` PASS. Log: `/tmp/kw356-rebase-suites.txt`.
- Host full inventory `./scripts/validate.sh` (no `--suite`) in the worktree at `e7223fc2`, direct backend, environment cleared: exit 0, 1469.99 s, no flake. Recorded in `.cache/final-validation.md`.
- Evidence comments: issuecomment-6261540736, issuecomment-6262406771.

## Known failures and unverified scope

- No known product failure on `e7223fc2`.
- No release, tag, or install in this finalize. A running holder keeps the old node prompt until its seat restarts.
- No live Sideagent node run was done. The tests simulate the node with the real state tool commands.
- Three Owner questions stay on issuecomment-6261540736: `keep_open` blocks a Sideagent retire; the cite path that the task records is a prompt instruction and not a tool gate; after a `returned`, the `maintenance-returned` alert references the task until the Host clears it. They were not re-decided here.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- scripts/kaola-acp-holder.py
- scripts/kaola-dispatch.py
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
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
- skills/kaola-project-runner/references/sideagent-node.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/references/sideagent-node.md
- tests/contract/test-issue-255-lifecycle-state.py

## Follow-Up Items

- None filed.
- No release, tag, or install in this finalize.

## Readiness

Host accepted `e7223fc2`. The Host full-gate result is reused. Merge sink into local main after #357, push to origin, close issue #356, release the claim label, archive.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-356/.cache/final-validation.md
- kaola-workflow/archive/issue-356/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-356/finalization-summary.md
- kaola-workflow/archive/issue-356/mission-ledger.jsonl
- kaola-workflow/archive/issue-356/workflow-state.md
