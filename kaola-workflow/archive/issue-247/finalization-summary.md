# Issue #247 finalization summary

## Delivered

A Codex manifest launch uses adapter `@agentclientprotocol/codex-acp` 2.0.1.
The child CLI is the absolute `CODEX_PATH` binary. The requested CLI is
`0.160.0` in `acp_requested_cli`. `acp_verified_versions` records
`cli=0.160.0;adapter=2.0.1;protocol=1` from the child this run launched.
PATH and the adapter's nested package do not select that child. An explicit
`--command` or `KAOLA_ACP_COMMAND` stays caller-owned.

Candidate: `fa607d18fe96332c192f8eb3ec41e22f8550704c`, parent
`1a090852b8dd5400d426ae0c61a213e285cc9e60`.
Accepted source commit, unamended: `caa84c382a1c199a053c4064680b0f6ff6e2b097`
(parent `c47daa1e8a1091eadadbca29aab6898695027083`).
Acceptance record: `acceptance.md`.

Evidence: one bounded seat `codex-kaola-247-child160` with marker
`CODEX247_CHILD160_ACP_OK`, `stop_reason` `end_turn`, and exact stop
`residual_pids []`. Receipts `/tmp/kpr247-start.json`,
`/tmp/kpr247-send.json`, and `/tmp/kpr247-stop.json`.
`./scripts/validate.sh` on this tip exited 0. Receipt
`/tmp/kpr247-validate.log` and `/tmp/kpr247-validate.exit`.
`run-chains --project issue-247` exited 1 with `chains_config_missing`: this
repo has no `package.json` `test:kaola-workflow:*` scripts. Consumer evidence
is `.cache/final-validation.md` (`verdict: pass`).

The Grok Bot bridge on this tip stays content stage, unpinned, and not
saveable. No release pin, release, tag, or installation is part of this issue.

## Documentation Impact

`docs/api.md` carries the launch and install sentence for the `CODEX_PATH`
child. This summary and the acceptance record are the finalize documentation.
No CHANGELOG release section.

## Known Failures and Unverified Scope

`./scripts/validate.sh` on this tip exited 0. The dispatch timeout assertion
still expects `start-timeout`, and that test passed. Bash watchdog skips stay
skips. No preview adapter was made the default. Shared-root Skill installation
was not required and was not done.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- docs/api.md
- platforms/codex.yaml
- scripts/kaola-acp.py
- scripts/render-skills.py
- scripts/validate.sh
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/SKILL.md
- skills/codex-kaola-project-runner/references/acp.md
- skills/codex-kaola-project-runner/references/platform.md
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/platform.yaml
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- tests/contract/test-issue-146-session-new-wait.py
- tests/contract/test-issue-22-bypass-all-approvals.py
- tests/contract/test-issue-247-codex-child.py
- tests/contract/test-runner-v2.py

## Follow-Up Items

No new follow-up is filed. The untracked harness diagnostic notes stay in the
main checkout and are not part of this commit.

## Final Readiness

Acceptance authorizes close, archive, the configured merge sink, and cleanup
for issue #247 only. The implementation candidate is frozen.
`caa84c382a1c199a053c4064680b0f6ff6e2b097` is not amended here. Lifecycle
results come from the transaction and sink receipts. No release, tag, package
publication, or install is authorized.

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
- kaola-workflow/archive/issue-247/.cache/final-validation.md
- kaola-workflow/archive/issue-247/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-247/acceptance.md
- kaola-workflow/archive/issue-247/finalization-summary.md
- kaola-workflow/archive/issue-247/mission-ledger.jsonl
- kaola-workflow/archive/issue-247/workflow-state.md
