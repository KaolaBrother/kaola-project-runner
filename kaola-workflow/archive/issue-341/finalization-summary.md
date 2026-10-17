# Finalization Summary — issue-341

## Delivered

Issue #341: an idle ACP session that receives real agent work after the last prompt already
ended is treated as a synthetic turn, then closed and woken on the same turn-end path.

- `scripts/kaola-acp-holder.py`: `is_agent_work_update()` treats non-empty assistant text or
  thoughts, tool activity, and a plan as agent work. Stray empty chunks and usage, config, or
  foreign-session noise do not open a turn and do not wake. An autonomous continuation opens a
  durable synthetic turn (`prompt_source="self"`, `agent_initiated=True`), and after the quiet
  period writes a second durable `turn_ended` (`outcome="agent_turn_completed"`). That close uses
  the existing turn-end wake path and emits one Delegator wake. A holder prompt or steer that
  arrives during the continuation does not emit a second `turn_ended` or a duplicate wake.
- The same holder copy is rendered into the eleven platform Skill trees.
- New suite `tests/contract/test-issue-341-agent-initiated-turn.py`, registered in both
  `scripts/validate.sh` lists (`python_suites_all` and `python_suites_b`), beside the #342 suite
  line that was already on main.

## Candidate

Branch `workflow/issue-341`, implementation commit `3e56bc912e78825628a120069cb7b6bdd78ceeb0`
(`fix(holder): treat idle-session agent updates as synthetic turns and wake Delegator (#341)`).
Rebased onto local main `76140a8c` (archive of #343). The pre-rebase commit was `1c549f24`.
14 files, +3117/−132. Not pushed. No upstream.

Host acceptance: ACCEPTED before this finalize. The Host reviewed the pre-rebase delivery and
instructed this offline local merge. Phase 1 on the rebased clean tree `3e56bc91` re-ran
`./scripts/render-skills.py --write` and `--check`, plus suites
`test-issue-341-agent-initiated-turn.py` and `test-issue-264-validate-lane-integrity.py`.
All three exited 0. `--write` left the tree clean.

## Evidence

- Phase 1 on clean `3e56bc91` in `.kw/worktrees/issue-341`: render `--write` exit 0, render
  `--check` exit 0, `./scripts/validate.sh --suite test-issue-341-agent-initiated-turn.py
  --suite test-issue-264-validate-lane-integrity.py` exit 0 (341: 4 tests OK; 264: 4 tests OK).
  Inherited `KAOLA_ZCODE_*` was cleared. `validate.sh` itself sets `KAOLA_LAUNCH_BACKEND=direct`.
- Recorded validation (`.cache/final-validation.md`) binds that worktree to the same command.
- Rebase onto `76140a8c` was clean. Both suite lines remain in both `validate.sh` lanes.
  `templates/grok-bot/accepted-revision.json` was already identical (`stage: content`).

## Known failures and unverified scope

- No known product failures.
- Whole-inventory `./scripts/validate.sh` was not run. The Host runs it on idle main after every
  seat stops, and pushes and closes issue #341 only after that run is green.
- Host boundary for this finalize: merge into local main only. Do not push. Do not close issue
  #341. Do not add a GitHub comment. Do not release, tag, install, or open a new issue.
  Keep-open is that deferral, not leftover product scope.
- Post-merge `./scripts/render-skills.py --write`, `--check`, and the two suites above run on
  local main after the sink. Their results are recorded in the user report, not in this
  pre-sink candidate record.
- This branch does not change the grok-bot pin. The bridge stays at the unpinned content stage
  already on main. The next release owns the pin.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- scripts/kaola-acp-holder.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- tests/contract/test-issue-341-agent-initiated-turn.py

## Follow-Up Items

- None filed. No run-discovered defect requires a new issue. `searched:` not applicable; nothing
  was filed.

## Readiness

Host accepted the #341 delivery. The rebased candidate `3e56bc91` is a fast-forward of local
main `76140a8c`. Validation is recorded pass. Local merge-sink and archive proceed. Issue #341
stays open. Publication to the remote waits for the Host.

## Finalize Findings

### claim_release_skipped_offline

This finalize released no claim: KAOLA_WORKFLOW_OFFLINE=1, so the release returned before making any forge call. Nothing local records whether this run was ever claimed online, so this does not assert the artifacts are there — but IF the claim was posted, the `workflow:in-progress` label and the `kw:claim` marker comment are still on the issues below. The marker expires after 24h; the label does not, and either one blocks a later claim of that issue until it is removed.

Issues whose claim release was skipped:

- #341

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-341/.cache/final-validation.md
- kaola-workflow/archive/issue-341/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-341/finalization-summary.md
- kaola-workflow/archive/issue-341/mission-ledger.jsonl
- kaola-workflow/archive/issue-341/workflow-state.md
