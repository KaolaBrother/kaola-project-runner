# Finalization Summary — issue-413

## Delivered

Issue #413 stages 1-2 (source presets, generated distribution, targeted validation), accepted by
the Host on 2026-10-27.

- Cursor: new escalation presets `cursor-cli/xhigh` (Grok 4.7, `grok-4.7-xhigh`, fast=false, Elite)
  and `cursor-cli/opus-xhigh` (Claude Opus 5.5, `claude-opus-5-5-xhigh`, Elite), Grok-style
  "Escalation level: use it when ... cannot solve the task." profiles; `cursor-cli/default` and
  `cursor-cli/opus` unchanged; `acp_model_map` gains `claude-opus-5-5-xhigh=claude-opus-5-5`.
- Droid: `droid/core` is DeepSeek V4.1 Flash 1017 (`deepseek-v4.1-flash-1017`,
  `reasoning_effort=max`, Elite) with the dsh default profile copied verbatim; static package map
  `deepseek-v4.1-flash-1017 -> core`, `kimi-k3` removed; launch_summary, docs/api.md updated.
- Generated skills, orchestrator profile catalog, README preset region and Grok Bot bridge
  (content stage) re-rendered.
- `reference_bytes` 8192 -> 9216 by Host decision (Option A), with the #68/#72 guards moved to the
  new ceiling.

## Candidate

Branch `workflow/issue-413`: `1249ba01` + `54dccee7` on base `10e755eb`.

## Evidence

- Catalog facts: `kaola-workflow/issue-413/catalog-evidence.md` (droid id/pool, Cursor xhigh,
  open tiers).
- Real-budget validation: `/tmp/kpr413-validate/real-render-check.log` (render --check PASS),
  `/tmp/kpr413-validate/real-suites.log` (11 suites OK, validate exit 0).
- Host acceptance: independent render --check PASS in the worktree, 2026-10-27.

## Known failures or unverified scope

- No live ACP smoke yet for the four affected presets (Host-owned later stage at the release
  boundary). Opus xhigh over Cursor ACP `effort` is unobserved live.
- `deepseek-v4.1-flash-1017` is rejected by the installed droid 0.241.1; it ships in the 0.249.0
  catalog behind the `deepseek_v4_1_flash_1017` feature flag (account state unknown). Release
  notes must carry this.
- Issue stages 3-4 (release, pin, three-Mac rollout) and the open questions (exact "open" tier
  referent; KPM companion URL) remain with the Host; the Host authorized closing #413 at this
  boundary.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- README.md
- docs/api.md
- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- platforms/cursor-cli.yaml
- platforms/droid.yaml
- scripts/adapters/cursor-cli.sh
- scripts/adapters/droid.sh
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/SKILL.md
- skills/cursor-cli-kaola-project-runner/references/platform.md
- skills/cursor-cli-kaola-project-runner/scripts/adapters/cursor-cli.sh
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/platform.yaml
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/SKILL.md
- skills/droid-kaola-project-runner/references/platform.md
- skills/droid-kaola-project-runner/scripts/adapters/droid.sh
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/platform.yaml
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/profile-catalog.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/budgets.json
- templates/grok-bot/accepted-revision.json
- tests/contract/fake-droid-acp-agent.py
- tests/contract/test-acp-contract.py
- tests/contract/test-droid-acp-contract.py
- tests/contract/test-generated-skills.py
- tests/contract/test-issue-111-model-tiers.py
- tests/contract/test-issue-148-quota-packages.py
- tests/contract/test-issue-218-preset-ids.py
- tests/contract/test-issue-68-heartbeat-snapshot.py
- tests/contract/test-issue-72-session-naming.py

## Follow-Up Items

- None filed by this run. Remaining stages are owned by the Host release stage (after #414).

## Readiness

Ready to finalize: all three missions done, Host acceptance recorded.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-413/.cache/final-validation.md
- kaola-workflow/archive/issue-413/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-413/catalog-evidence.md
- kaola-workflow/archive/issue-413/finalization-summary.md
- kaola-workflow/archive/issue-413/mission-ledger.jsonl
- kaola-workflow/archive/issue-413/workflow-state.md
