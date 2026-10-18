# Finalization Summary — issue-349

## Delivered

Issue #349: a wrong verb on an unchanged Host-owned checkpoint input settles as retained, and that class does not wake the Host.

- A selected `host:<kind>/<id>@<rev>` whose current record is still that revision, was written by the Host (`writer` `host` or `host:…`), and names `owner`, `next` or `wait`, settles as retained whichever verb the node used. It is not returned and does not open `maintenance-returned`.
- The node prompt, `sideagent-node.md`, and `duty-reconcile.md` each say once that a Host decision row is `retained`, or `retired:decisions/<id>` when the row is gone, never `applied`.
- A `maintenance-returned` alert whose inputs are all of this class does not wake the Host. Delegator dedup (#302, #324) and coverage (#310) are unchanged.
- One unreproduced `checkpoint: missing` with no `missing_sources` is not part of this change. The 10:34:06 missing stays the known #336 refusal-and-fallback path.
- `docs/api.md` and CHANGELOG Unreleased state the rule. Seats: restart required. This content commit leaves the Grok Bot bridge unpinned (`saveable: false`).

## Candidate

Branch `workflow/issue-349`, parent local `main` `d4cdad9995ec730a7bd9d7c56ea3aae8e79fcfa3`.

- `b34cafa851a3a3b70636f3c7238be161ace5d13b` — `fix: settle a wrong verb on an unchanged Host-owned checkpoint input as retained (#349)`

Acceptance candidate: `b34cafa851a3a3b70636f3c7238be161ace5d13b`. Worktree clean. Not pushed. This finalize does not add an implementation commit.

Host acceptance: ACCEPTED.

## Evidence

- Full inventory `./scripts/validate.sh` (no `--suite`), worktree clean at `b34cafa8`: 128 suites, exit 0, wall 1571.66 s. Log: `/tmp/kpr-run/full-validate-349-b34cafa8.log` (`validate: candidate: b34cafa8 (clean)`, `VALIDATE_EXIT=0`). No flake. The same commit is still the worktree HEAD, so that voucher is reused and the suite is not re-run.
- Host voucher also records fail-on-main at `d4cdad99` (temporary worktree plus the test file): 10 failures of 39 tests. Focused suites 349, 255, 324, 302, 264 plus render were green (226 s). Core review passed on `standing_host_owned_input`, the node prompt sentence, and `_attention_is_only_standing_return`.
- Mission ledger `kaola-workflow/.ledger/issue-349.jsonl`: two missions `done`. Those lines are not rewritten.

## Known failures and unverified scope

- No known product failure on `b34cafa8`.
- R1396's single `checkpoint: missing` was not reproduced and is not claimed fixed.
- Host boundary for this finalize: merge into local main only. Do not push. Do not close issue #349. Do not add a GitHub comment. Do not release, tag, install, or open a new issue. Keep-open is that deferral. Offline mode makes no forge call, so the claim label is not released here.
- Post-merge `./scripts/render-skills.py --write` and `--check` run on local main after the sink. No validate suite is re-run; the full gate already passed on this same commit.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- scripts/kaola-acp-holder.py
- scripts/kaola-dispatch.py
- scripts/kaola-record-contract.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/antigravity-kaola-project-runner/scripts/kaola-record-contract.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-record-contract.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-record-contract.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-record-contract.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-record-contract.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-record-contract.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-record-contract.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/duty-reconcile.md
- skills/kaola-project-runner/references/sideagent-node.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kaola-project-runner/scripts/kaola-record-contract.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/grok-bot/accepted-revision.json
- templates/orchestrator/references/duty-reconcile.md
- templates/orchestrator/references/sideagent-node.md
- tests/contract/test-issue-349-checkpoint-verb.py

## Follow-Up Items

- None filed. No run-discovered defect requires a new issue. `searched:` not applicable; nothing was filed.

## Readiness

Host accepted the change. The full-gate voucher on `b34cafa8` is reused. Local merge-sink and archive proceed. Issue #349 stays open. Publication to the remote waits for the Host.

## Finalize Findings

### claim_release_skipped_offline

This finalize released no claim: KAOLA_WORKFLOW_OFFLINE=1, so the release returned before making any forge call. Nothing local records whether this run was ever claimed online, so this does not assert the artifacts are there — but IF the claim was posted, the `workflow:in-progress` label and the `kw:claim` marker comment are still on the issues below. The marker expires after 24h; the label does not, and either one blocks a later claim of that issue until it is removed.

Issues whose claim release was skipped:

- #349

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-349/.cache/final-validation.md
- kaola-workflow/archive/issue-349/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-349/finalization-summary.md
- kaola-workflow/archive/issue-349/mission-ledger.jsonl
- kaola-workflow/archive/issue-349/workflow-state.md
