# Finalization Summary — issue-341 (repair run)

## Delivered

Repair of the #341 regression from 3e56bc91. On fd05fa3d, 8 suites failed deterministically. One
more Host decision was folded in.

- `72c57c34` holder: a synthetic agent-initiated turn opens only when the holder's last turn
  completed (`self.turn.outcome in COMPLETED_TURN_OUTCOMES`). A probe over the 8 suites recorded
  119 idle agent-work updates (/tmp/kpr-341r/probe.jsonl). Every one was the fake ZCode
  app-server's `[interaction-result]` agent_message_chunk, streamed at session create before any
  prompt. The synthetic turn it opened made the first `send` answer `prompt-in-progress`. A send
  during a synthetic turn keeps that active-turn answer. An after-turn steer is queued and is
  delivered when the synthetic turn closes. Tests (d) pre-prompt replay and (e) post-cancel tail
  were added.
- `c51e0091` test-issue-295: the devin/default `default_effort` expectation is now `max`. #342
  (974b54f4) changed `platforms/devin.yaml`; this is a separate causal class.
- `09c13156` Host decisions:
  - `AGENT_TURN_QUIET_DEFAULT` 1.5 → 60.0 s and `AGENT_TURN_QUIET_MAX` 60 → 600 s. A replay of
    the real incident at 1.5 s gave ~58 pseudo turns; at 60 s it gives 4.
  - The ZCode bridge emits `usage_update{stopReason}` for a backend turn terminal with no ACP
    prompt in flight. The holder's `idle_signaled` path closes the synthetic turn at once. The
    rid path is byte-identical.
  - Tests: quiet default assertion, (f1) bridge frame unit test, (f2) explicit-idle end-to-end.

## Candidate

Branch `workflow/issue-341` @ `09c13156` on top of local main `fd05fa3d` (fast-forward). Not pushed.
Host acceptance: ACCEPTED. The Host re-ran test-issue-341 / 70 / 76 / 295 and render `--check` on
clean 09c13156; all green.

## Evidence

- Baseline on main fd05fa3d, 8 suites: exit 1, all 8 failed. Log:
  /tmp/kpr-341r/logs/baseline-fd05fa3d-8.log
- New cases d/e fail on the fd05fa3d holder: /tmp/kpr-341r/logs/t341-old-holder.log
- f2 fails with `idle_signaled` removed: /tmp/kpr-341r/logs/t341-f2-no-idle.log
- 15 suites on the candidate bytes: exit 0. Log: /tmp/kpr-341r/logs/after2-15.log
- test-341 run 3 times: OK. Log: /tmp/kpr-341r/logs/t341b-x3.log
- render `--check`: exit 0
- Recorded validation: `.cache/final-validation.md`

## Known failures and unverified scope

- No known product failures.
- Whole-inventory `./scripts/validate.sh` was not run. The Host runs it on idle main after the
  merge.
- Host boundary: merge into local main only. No push. Do not close or comment on #341. No release,
  tag, install, or new issue. Keep-open is that deferral, not leftover product scope.
- Agents without an explicit idle signal close a synthetic turn after up to 60 s. Until then the
  holder answers `send` with `prompt-in-progress`. This was accepted by the Host decision.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- scripts/kaola-acp-holder.py
- scripts/kaola-zcode-acp.py
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
- skills/zcode-kaola-project-runner/scripts/kaola-zcode-acp.py
- tests/contract/test-issue-295-delegator-seats.py
- tests/contract/test-issue-341-agent-initiated-turn.py

## Follow-Up Items

- None filed. Nothing new was discovered that needs an issue: the 295 cause was fixed in this run.
  `searched:` not applicable.

## Readiness

The Host accepted the change, and validation is recorded as pass. The local merge sink and archive
proceed. Issue #341 stays open. Publication to the remote waits for the Host.

## Finalize Findings

### claim_release_skipped_offline

This finalize released no claim: KAOLA_WORKFLOW_OFFLINE=1, so the release returned before making any forge call. Nothing local records whether this run was ever claimed online, so this does not assert the artifacts are there — but IF the claim was posted, the `workflow:in-progress` label and the `kw:claim` marker comment are still on the issues below. The marker expires after 24h; the label does not, and either one blocks a later claim of that issue until it is removed.

Issues whose claim release was skipped:

- #341

## Sink Findings

post_rebase_tests: skipped

archive_collision: kaola-workflow/archive/issue-341/ already existed, so this run was archived to kaola-workflow/archive/issue-341.archived-2026-10-17T04-13-34-571Z/ instead. The pre-existing directory was left exactly where it was — a SECOND archive standing for this project, no part of this one. What it holds, and whether the repository tracks it at all, is not recorded here: read it before treating this archive as the run's whole record.

archived_paths:
- kaola-workflow/archive/issue-341.archived-2026-10-17T04-13-34-571Z/.cache/final-validation.md
- kaola-workflow/archive/issue-341.archived-2026-10-17T04-13-34-571Z/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-341.archived-2026-10-17T04-13-34-571Z/finalization-summary.md
- kaola-workflow/archive/issue-341.archived-2026-10-17T04-13-34-571Z/mission-ledger.jsonl
- kaola-workflow/archive/issue-341.archived-2026-10-17T04-13-34-571Z/workflow-state.md
