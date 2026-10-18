# Finalization Summary — issue-347

## Delivered

Issue #347: a read-only Command Code usage probe for the `dsh/commandcode` tier.

- `scripts/kaola-quota.py --platform dsh --model commandcode/deepseek/deepseek-v4.1-flash --probe` reads `COMMANDCODE_API_KEY` from the process environment, then `$DSH_HOME` or `~/.dsh` `.env`, then `.credentials.yaml` `refs:`.
- The primary route is `GET /alpha/billing/credits`. Optional `/alpha/billing/subscriptions` and `/alpha/usage/summary` add plan id, period end, and period spend, requests, and tokens. A failed optional route omits that object.
- Windows are `5h`, `weekly`, and `monthly`. Primary `quota` is the most constrained window. The result envelope matches the Antigravity usage object for package `dsh:commandcode`.
- A missing key is `key_missing`. HTTP 401/403/404/410, 429, 5xx, timeout, network failure, and a missing `windowLimits` are `unavailable`. The probe does not call `/alpha/whoami`, does not keep identity fields, does not print or store the key or the raw body, and does not raise.
- `opencode-go/...` stays on the OpenCode package. The Antigravity probe is unchanged.
- The invocation and schema are in `docs/api.md`. README mentions the probe. CHANGELOG Unreleased states `Seats: restart required` because `scripts/kaola-quota.py` is in the operator restart set.
- Generated worker copies come from `./scripts/render-skills.py --write`.

## Candidate

Branch `workflow/issue-347`, parent local `main` `81421691fb8870adec77eb226a5ddfa65b6cfe34`.

- `5e029aa4162c52978e9d9c56b5920761b7f08c85` — `feat: add a read-only Command Code usage probe (#347)`

Acceptance candidate: `5e029aa4162c52978e9d9c56b5920761b7f08c85`. Worktree clean. Not pushed. This finalize does not add an implementation commit.

Host acceptance: ACCEPTED. The pre-merge full gate on this commit is green. The Host also reproduced both live receipts.

## Evidence

- Full inventory `./scripts/validate.sh` (no `--suite`), worktree clean at `5e029aa4`: 127 suites, exit 0, wall 1492.76 s. Log: `/tmp/kpr-run/full-validate-347-5e029aa4.log` (`validate: candidate: 5e029aa4 (clean)`, `VALIDATE_EXIT=0`). No flake. The same commit is still the worktree HEAD, so that voucher is reused and the suite is not re-run.
- Host live receipts on this commit: `status: ok` with windows `5h`, `weekly`, and `monthly`, primary window `weekly`, and a plan object; `key_missing` with `COMMANDCODE_API_KEY` unset and `DSH_HOME` an empty directory. Both outputs had no key and no identity fields.
- Mission ledger `kaola-workflow/.ledger/issue-347.jsonl`: three missions `done`. Those lines are not rewritten.

## Known failures and unverified scope

- No known product failure on `5e029aa4`.
- Host boundary for this finalize: merge into local main only. Do not push. Do not close issue #347. Do not add a GitHub comment. Do not release, tag, install, or open a new issue. Keep-open is that deferral. Offline mode makes no forge call, so the claim label is not released here.
- Post-merge `./scripts/render-skills.py --write` and `--check` run on local main after the sink. No validate suite is re-run; the full gate already passed on this same commit.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- README.md
- docs/api.md
- scripts/kaola-quota.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-quota.py
- skills/claude-code-kaola-project-runner/scripts/kaola-quota.py
- skills/codex-kaola-project-runner/scripts/kaola-quota.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-quota.py
- skills/devin-kaola-project-runner/scripts/kaola-quota.py
- skills/droid-kaola-project-runner/scripts/kaola-quota.py
- skills/dsh-kaola-project-runner/scripts/kaola-quota.py
- skills/grok-kaola-project-runner/scripts/kaola-quota.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-quota.py
- skills/opencode-kaola-project-runner/scripts/kaola-quota.py
- skills/zcode-kaola-project-runner/scripts/kaola-quota.py
- tests/contract/test-issue-347-commandcode-usage.py

## Follow-Up Items

- None filed. No run-discovered defect requires a new issue. `searched:` not applicable; nothing was filed.

## Readiness

Host accepted the change. The full-gate voucher on `5e029aa4` is reused. Local merge-sink and archive proceed. Issue #347 stays open. Publication to the remote waits for the Host.

## Finalize Findings

### claim_release_skipped_offline

This finalize released no claim: KAOLA_WORKFLOW_OFFLINE=1, so the release returned before making any forge call. Nothing local records whether this run was ever claimed online, so this does not assert the artifacts are there — but IF the claim was posted, the `workflow:in-progress` label and the `kw:claim` marker comment are still on the issues below. The marker expires after 24h; the label does not, and either one blocks a later claim of that issue until it is removed.

Issues whose claim release was skipped:

- #347

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-347/.cache/final-validation.md
- kaola-workflow/archive/issue-347/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-347/finalization-summary.md
- kaola-workflow/archive/issue-347/mission-ledger.jsonl
- kaola-workflow/archive/issue-347/workflow-state.md
