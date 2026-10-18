# Finalization Summary — issue-352

## Delivered

Issue #352: the droid platform waits 60 s for `session/new`.

- `platforms/droid.yaml` sets `acp_session_new_timeout` to `"60"`, beside the other `acp_*` keys. The rendered copy `skills/droid-kaola-project-runner/scripts/platform.yaml` matches it. The shared 15 s default and every other platform are unchanged. Codex stays 60 s.
- A live Droid `session/new` on v0.9.19 answered after about 24 s, past the shared 15 s default, and `start` returned `acp-session-timeout`. The holder and `kaola-acp.py` already honour this key (Issue #146). This run does not change that logic.
- `docs/api.md` records that Codex and Droid both declare `60`, and that an absent key still means 15 s. The generated Droid `references/acp.md` sentence is the general key meaning and stays as written.
- Seats: restart required. `platforms/droid.yaml` is in the operator restart set, so a running droid seat keeps its holder's previous wait until that seat restarts. The Grok Bot bridge stays unpinned (`saveable: false`).

## Candidate

Branch `workflow/issue-352`, parent local `main` `93d358b93544656eccad1755a229b19a0eff3dae`.

- `4374fc54410e89fe463527f51bd7a1765189d70e` — `Raise the droid session/new wait to 60 seconds (#352)`

Acceptance candidate: `4374fc54410e89fe463527f51bd7a1765189d70e`. Worktree clean. Not pushed. This finalize does not add an implementation commit.

Host acceptance: ACCEPTED.

## Evidence

- Full inventory `./scripts/validate.sh` (no `--suite`), worktree clean at `4374fc54`: 132 suites, exit 0, wall 1543.33 s. Log: `/tmp/kpr-run/full-validate-352-4374fc54.log` (`validate: candidate: 4374fc54 (clean)`, `validate: coverage: FULL INVENTORY (132 suites; no-argument run)`, `VALIDATE_EXIT=0`). The same commit is still the worktree HEAD, so that voucher is reused and the suite is not re-run.
- Before the fix, `tests/contract/test-issue-352-droid-session-timeout.py` on `93d358b9` exited 1. After `4374fc54` the same file exited 0.
- Mission ledger `kaola-workflow/.ledger/issue-352.jsonl`: one mission `done`. That line is not rewritten.

## Known failures and unverified scope

- No known product failure on `4374fc54`.
- Host boundary for this finalize: merge into local main only. Do not push. Do not close issue #352. Do not add a GitHub comment. Do not release, tag, install, or open a new issue. Keep-open is that deferral. Offline mode makes no forge call, so the claim label is not released here.
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
- platforms/droid.yaml
- scripts/validate.sh
- skills/droid-kaola-project-runner/scripts/platform.yaml
- tests/contract/test-issue-146-session-new-wait.py
- tests/contract/test-issue-352-droid-session-timeout.py

## Follow-Up Items

- None filed. No run-discovered defect requires a new issue.

## Readiness

Host accepted the change. The full-gate voucher on `4374fc54` is reused. Local merge-sink and archive proceed. Issue #352 stays open. Publication to the remote waits for the Host.

## Finalize Findings

### claim_release_skipped_offline

This finalize released no claim: KAOLA_WORKFLOW_OFFLINE=1, so the release returned before making any forge call. Nothing local records whether this run was ever claimed online, so this does not assert the artifacts are there — but IF the claim was posted, the `workflow:in-progress` label and the `kw:claim` marker comment are still on the issues below. The marker expires after 24h; the label does not, and either one blocks a later claim of that issue until it is removed.

Issues whose claim release was skipped:

- #352

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-352/.cache/final-validation.md
- kaola-workflow/archive/issue-352/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-352/finalization-summary.md
- kaola-workflow/archive/issue-352/mission-ledger.jsonl
- kaola-workflow/archive/issue-352/workflow-state.md
