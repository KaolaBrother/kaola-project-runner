# Issue 254 finalization summary

## Delivered

OpenCode 2.0.22 publishes `opencode-go/deepseek-v4.1-flash` after `session/new`. Setting that id before the advertisement returns JSON-RPC -32602 and leaves `opencode/fledge-alpha-free`. Start now waits, bounded, until the live option list contains the requested id, then sets it once, with no substitution.

The DSH `--version` catalog-missing flag is recorded as `catalog_probe.reporting_gap` `version-probe-does-not-list-acp-models`. The candidate id and the resolution state are unchanged. DSH was not retested.

The Grok Bot bridge is the unpinned content stage because this change follows the v0.8.1 pin. It is not saveable. No pin, tag, release, or shared Skill-root install.

## Candidate

Candidate: `a7de008ceccab3d9a18982e6c113ab4a7fd02e57`
Subject: `fix(opencode): set DeepSeek V4.1 Flash after the provider is advertised`
Branch: `workflow/issue-254`
Worktree: `/Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-254`
Parent and baseline main at acceptance: `bacf2569fc1cfcc8110a1641ce65246f4f535e11`

The Host accepts this commit. This close-out does not amend `a7de008`.

## Evidence

Reused, not rerun, and bound to this commit:

- Probes: `/tmp/kpr-i254/probe-immediate.json` (immediate set returns -32602) and `/tmp/kpr-i254/probe-wait.json` (the same set applies after the advertisement).
- Live session `opencode-KPR-i254-repro`, OpenCode 2.0.22, acp `ses_efa899932ffeipCt65X4GBlDHk`.
- `/tmp/kpr-i254/live-start.json`: `config_application.model.applied` true, value `opencode-go/deepseek-v4.1-flash`, `effective_model` the same id.
- `/tmp/kpr-i254/live-status.json`: model `currentValue` is that id.
- `/tmp/kpr-i254/live-send.json`: `final_text` `KPR_OPENCODE_ACP_OK`, `stop_reason` `end_turn`, `mutation_status` `completed`.
- `/tmp/kpr-i254/live-stop.json`: `stopped` true, `residual_pids` [].
- `./scripts/validate.sh` on this worktree, with `FORCE_COLOR` and `CLICOLOR_FORCE` unset and `NO_COLOR=1` (`CLICOLOR=0` also set), recorded `VALIDATE:0` and exit code 0.

The binding is `.cache/final-validation.md`, recorded from the issue 254 worktree.

## Known failures or unverified scope

No failure on this candidate. No shared Skill-root install, pin, tag, or release is authorized, and none is performed. DSH was not retested. Other runtimes were not live-smoked. Issue 254 is the only issue this close-out may close.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- platforms/opencode.yaml
- scripts/kaola-acp.py
- scripts/kaola-model-policy.py
- scripts/validate.sh
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-model-policy.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-model-policy.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-model-policy.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-model-policy.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-model-policy.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-model-policy.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-model-policy.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-model-policy.py
- skills/opencode-kaola-project-runner/references/acp.md
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-model-policy.py
- skills/opencode-kaola-project-runner/scripts/platform.yaml
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-model-policy.py
- templates/grok-bot/accepted-revision.json
- tests/contract/mock-acp-agent.py
- tests/contract/test-issue-254-opencode-model.py

## Follow-Up Items

None. This run filed no follow-up. The measured OpenCode advertisement race is the change this candidate delivers. The DSH reporting gap is already recorded in KPR-owned state.

## Readiness

Ready for the merge sink and close of issue 254 only.

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
- kaola-workflow/archive/issue-254/.cache/final-validation.md
- kaola-workflow/archive/issue-254/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-254/finalization-summary.md
- kaola-workflow/archive/issue-254/mission-ledger.jsonl
- kaola-workflow/archive/issue-254/workflow-state.md
