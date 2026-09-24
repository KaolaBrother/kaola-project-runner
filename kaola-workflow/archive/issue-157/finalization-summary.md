# Finalization summary — issue-157

## Delivered
Issue #157 lands the Owner-accepted #156 Skill-prompt review (receipt `.kaola/skill-prompt-review-2026-09-24.md`, checklist comment https://github.com/KaolaBrother/kaola-project-runner/issues/157#issuecomment-5807277785) in §7 order:
- f968ba1 accuracy (orchestrator): PR-C1/X4, PR-C3, PR-C4/X3, PR-C5, PR-C6, PR-C7, X1, X5–X9, X11 + PR-R1 (paired cut required by the 17,408 B main budget)
- acd40f3 accuracy (workers): W-A1…W-A11, W-C1…W-C4, R1
- 592caec budget relief: KD-R1, PR-C2/X2, PR-R3 unconditional part; R7 = not shown → skeleton lines 38–41 kept
- 54703ea budget relief (workers): T3 + P1
- 15ad5c5 move-outs: PR-M1, PR-M2 (+X10), PR-R4
- 36eaeff Low/Nit (orchestrator/Delegator): §1.2 rows, PR-R2, PR-M3, KD-C1, §1.4, KD-R3, KD-A1…A3 (KD-R2 satisfied, KD-S1 no change)
- 43d3062 fleet wordiness: T1, T2, T4–T9, T14, T15, manifest cuts
- 063cb42 S1/S2 retired, S3 → docs (S4 no change)
- f3351e9 doc docking

## Files Changed
templates/orchestrator/**, templates/kaola-delegator/**, templates/SKILL.md.tmpl, templates/references/*.tmpl, platforms/*.yaml, scripts/render-skills.py (worker render helpers), generated skills/**, 17 contract tests, docs (README, host-entry-evidence, issue-dispatch-display, zcode-host, api), README.md, CHANGELOG.md.

## Test Coverage
17 prose-pinned contract tests updated in the same commit as the prose they pin (test-issue-41, -49, -52, -65, -68, -70, -72, -74, -75, -86, -92, -94, -118, -133, -147, test-progressive-disclosure, test-zcode-heartbeat-contract). Second reviewer claude-code-KPR-i157-review-2 ran the 17 changed tests at all 8 stage commits (failures matched base exactly).

## Validation
- `./scripts/render-skills.py --check` rc=0 and `./scripts/validate.sh` rc=0 on 063cb42 (Host-accepted candidate) and again on f3351e9 (doc-docked candidate), Mac Studio, bash 3.2 (watchdog rows skipped by design, #151). Recorder: `.cache/final-validation.md` verdict pass.
- Stage 3 (pre-rebuild 880bb1e) had failed validate rc=1 on test-issue-75 (moved `trigger:"auto"` pin); fixed inside the stage-3 commit before the rebuild.
- Host acceptance: ACCEPT (Host spot-checks + second reviewer ACCEPT-WITH-NOTES: §6 R1–R14 PASS, mapping PASS, pinned-test integrity PASS, budgets PASS).

## Changed Paths
- CHANGELOG.md
- README.md
- docs/README.md
- docs/api.md
- docs/host-entry-evidence.md
- docs/issue-dispatch-display.md
- docs/zcode-host.md
- platforms/claude-code.yaml
- platforms/codex.yaml
- platforms/cursor-cli.yaml
- platforms/devin.yaml
- platforms/droid.yaml
- platforms/dsh.yaml
- platforms/grok.yaml
- platforms/kimi-cli.yaml
- platforms/opencode.yaml
- platforms/zcode.yaml
- scripts/render-skills.py
- skills/claude-code-kaola-project-runner/SKILL.md
- skills/claude-code-kaola-project-runner/references/acp.md
- skills/claude-code-kaola-project-runner/references/platform.md
- skills/claude-code-kaola-project-runner/references/steering.md
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/platform.yaml
- skills/codex-kaola-project-runner/SKILL.md
- skills/codex-kaola-project-runner/references/acp.md
- skills/codex-kaola-project-runner/references/platform.md
- skills/codex-kaola-project-runner/references/steering.md
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/platform.yaml
- skills/cursor-cli-kaola-project-runner/SKILL.md
- skills/cursor-cli-kaola-project-runner/references/acp.md
- skills/cursor-cli-kaola-project-runner/references/platform.md
- skills/cursor-cli-kaola-project-runner/references/steering.md
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/platform.yaml
- skills/devin-kaola-project-runner/SKILL.md
- skills/devin-kaola-project-runner/references/acp.md
- skills/devin-kaola-project-runner/references/platform.md
- skills/devin-kaola-project-runner/references/steering.md
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/platform.yaml
- skills/droid-kaola-project-runner/SKILL.md
- skills/droid-kaola-project-runner/references/acp.md
- skills/droid-kaola-project-runner/references/platform.md
- skills/droid-kaola-project-runner/references/steering.md
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/platform.yaml
- skills/dsh-kaola-project-runner/SKILL.md
- skills/dsh-kaola-project-runner/references/acp.md
- skills/dsh-kaola-project-runner/references/platform.md
- skills/dsh-kaola-project-runner/references/steering.md
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/platform.yaml
- skills/grok-kaola-project-runner/SKILL.md
- skills/grok-kaola-project-runner/references/acp.md
- skills/grok-kaola-project-runner/references/platform.md
- skills/grok-kaola-project-runner/references/steering.md
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/platform.yaml
- skills/kaola-delegator/SKILL.md
- skills/kaola-delegator/references/handoff.md
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/doc-maintenance.md
- skills/kaola-project-runner/references/heartbeat-skeleton.md
- skills/kaola-project-runner/references/host-entry-matrix.md
- skills/kaola-project-runner/references/host-startup.md
- skills/kaola-project-runner/references/issue-dispatch.md
- skills/kaola-project-runner/references/workflow-worktree.md
- skills/kaola-project-runner/references/zcode-host-dispatch.md
- skills/kaola-project-runner/references/zcode-native-skill-entry.md
- skills/kimi-cli-kaola-project-runner/SKILL.md
- skills/kimi-cli-kaola-project-runner/references/acp.md
- skills/kimi-cli-kaola-project-runner/references/platform.md
- skills/kimi-cli-kaola-project-runner/references/steering.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/kimi-cli-kaola-project-runner/scripts/platform.yaml
- skills/opencode-kaola-project-runner/SKILL.md
- skills/opencode-kaola-project-runner/references/acp.md
- skills/opencode-kaola-project-runner/references/platform.md
- skills/opencode-kaola-project-runner/references/steering.md
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/platform.yaml
- skills/zcode-kaola-project-runner/SKILL.md
- skills/zcode-kaola-project-runner/references/acp.md
- skills/zcode-kaola-project-runner/references/platform.md
- skills/zcode-kaola-project-runner/references/steering.md
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/platform.yaml
- templates/SKILL.md.tmpl
- templates/kaola-delegator/SKILL.md.tmpl
- templates/kaola-delegator/references/handoff.md.tmpl
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/doc-maintenance.md
- templates/orchestrator/references/heartbeat-skeleton.txt
- templates/orchestrator/references/host-entry-matrix.md
- templates/orchestrator/references/host-startup.md.tmpl
- templates/orchestrator/references/issue-dispatch.md
- templates/orchestrator/references/workflow-worktree.md
- templates/orchestrator/references/zcode-host-dispatch.md.tmpl
- templates/orchestrator/references/zcode-native-skill-entry.md
- templates/references/acp.md.tmpl
- templates/references/platform.md.tmpl
- templates/references/steering.md.tmpl
- tests/contract/test-issue-118-seat-cap.py
- tests/contract/test-issue-133-mission-ledger.py
- tests/contract/test-issue-147-installed-survey.py
- tests/contract/test-issue-41-orchestrator.py
- tests/contract/test-issue-49-grok-bot-host.py
- tests/contract/test-issue-52-workflow-worktree.py
- tests/contract/test-issue-65-host-contract.py
- tests/contract/test-issue-68-heartbeat-snapshot.py
- tests/contract/test-issue-70-binding-fact.py
- tests/contract/test-issue-72-session-naming.py
- tests/contract/test-issue-74-kaola-delegator.py
- tests/contract/test-issue-75-codex-compact-hook.py
- tests/contract/test-issue-86-delegator-quota.py
- tests/contract/test-issue-92-permission-wake-recovery.py
- tests/contract/test-issue-94-zcode-native-skill-entry.py
- tests/contract/test-progressive-disclosure.py
- tests/contract/test-zcode-heartbeat-contract.py

## Documentation Docking
DOCKED — `.cache/doc-docking.md`.

## Measured
At 063cb42, `wc -c` of rendered surfaces vs baseline 26cee00: Project Runner 74,376 → 63,614 B (−10,762); Kaola-Delegator 13,159 → 12,640 B (−519); ten workers 289,867 → 233,631 B (−56,236). Tightest headroom after edit: Delegator SKILL 217 B, handoff 332 B, host-startup 474 B; bridge untouched (2,555/2,560).

## Follow-Up Items
- filed: #158 (P3, bug) — dsh invalid `--permission-mode` refusal names the internal `--mode` flag (kaola-acp.py:3374). Confirmed exists, body non-empty (1,304 chars).
- Reviewer awareness notes (no action): the PR-R3 skeleton step-2 cut removed the permission-wake non-loss sentence from the loaded surface (R10 core pins survive); T6 "binds" wording nuance.
- Receipt §5 out-of-scope observations remain as recorded there (bridge wording, kaola-tmux.sh usage text, dead adapter_build_launch, invariant-pinning test redesign); not filed by this run.

## Readiness
READY — accepted, validated, docked; sink-merge next.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-157/.cache/doc-docking.md
- kaola-workflow/archive/issue-157/.cache/final-validation.md
- kaola-workflow/archive/issue-157/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-157/finalization-summary.md
- kaola-workflow/archive/issue-157/mission-ledger.jsonl
- kaola-workflow/archive/issue-157/workflow-state.md
