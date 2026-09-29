# Issue 237 — consumer model names separate from effort

## Delivered
Downstream consumers can read a model identity without appended reasoning effort, and can read preset, requested, resolved, applied, and current effort as separate facts. Claude Code `default` and `opus-xhigh` share the display name Opus 5.5 with launch efforts medium and xhigh. Devin display names are SWE-2, Opus Fusion, and Fable Fusion; declared component efforts live in `*_model_components` and do not enter launch effort, argv, or `set_config_option`. Preset IDs, native model IDs, profiles, classes, quota bindings, and launch efforts are unchanged.

## Candidate
4d58dd7a822c19745d0a02257518e77dc1ab354a, workflow/issue-237.
Worktree: /Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-237

## Evidence and acceptance
Host ACCEPTANCE: PASS. The Host judged the pre-commit diff on workflow/issue-237 (52 files, +1933/−313) against the issue's minimal design and acceptance 1–6, then asked finalize to commit the new test with that delivery. Implementation commit 4d58dd7a adds that test (53 files, +2135/−313).
Host reruns, all green: `./scripts/render-skills.py --check` exit 0 (content stage, budgets OK); `python3 tests/contract/test-issue-237-model-display.py` OK (5); `python3 tests/contract/test-issue-218-preset-ids.py` OK; `python3 tests/contract/test-issue-111-model-tiers.py` OK; `python3 tests/contract/test-issue-148-quota-packages.py` OK; `python3 tests/contract/test-generated-skills.py` PASS; `python3 tests/contract/test-acp-contract.py` OK, including explicit-effort rejection, bare `--model`, preserved resume, and Devin argv with no effort write.
Grok bridge and guide surfaces had zero diff, so pin-stage checks were not triggered. Protected files were not staged or deleted. No release, tag, install, or CHANGELOG release section.

## Known failures or unverified scope
No remaining failure in the affected checks. No ten-platform model, price, or capability probe. Direct unknown native IDs stay unnamed (`model_display.name` null) rather than guessed. Devin component effort is declared catalog knowledge, not a current observation. Old holders lack `model_display` until a new start.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- README.md
- docs/api.md
- platforms/claude-code.yaml
- platforms/devin.yaml
- scripts/adapters/claude-code.sh
- scripts/adapters/devin.sh
- scripts/kaola-acp-holder.py
- scripts/kaola-acp.py
- scripts/render-skills.py
- skills/claude-code-kaola-project-runner/SKILL.md
- skills/claude-code-kaola-project-runner/references/platform.md
- skills/claude-code-kaola-project-runner/scripts/adapters/claude-code.sh
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/platform.yaml
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/SKILL.md
- skills/devin-kaola-project-runner/references/platform.md
- skills/devin-kaola-project-runner/scripts/adapters/devin.sh
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/platform.yaml
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/profile-catalog.md
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- tests/contract/mock-acp-agent.py
- tests/contract/test-acp-contract.py
- tests/contract/test-issue-111-model-tiers.py
- tests/contract/test-issue-218-preset-ids.py
- tests/contract/test-issue-237-model-display.py

## Follow-Up Items
None.

## Readiness
Ready to merge and close issue #237.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-237/.cache/final-validation.md
- kaola-workflow/archive/issue-237/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-237/finalization-summary.md
- kaola-workflow/archive/issue-237/mission-ledger.jsonl
- kaola-workflow/archive/issue-237/workflow-state.md
