# Finalization Summary — issue-189

## Delivered
Issue #189 (精简 Delegator/Host 调度提示词，复用既有 Workflow 规则), accepted by Host on frozen candidate 8bf9db2; docking commit 47cd9f4 adds the CHANGELOG Unreleased entry.
- Host dispatch: a clear task goes directly to a suitable authorized worker as a new session; split/parallelize only when the work needs it; the count is a ceiling, not a target to fill (render-skills.py IDLE_BEFORE_STOP, orchestrator step 2, heartbeat skeleton step 2). Hard cap, stop-before-start, "never invent work or expand authorization" kept verbatim.
- Host acceptance: Host judges actual diff and existing run records against the currently effective global Workflow rules, reuses sufficient same-candidate evidence, returns only concrete deviations/omissions/invalidated evidence to the same worker (orchestrator step 3, heartbeat step 3). Default distinct-verifier requirement removed. Acceptance-before-finalize and no prose/idle/CI/exit substitution kept.
- Delegator: relays user changes and follows up at the user's agreed cadence; first-beat check and prohibitions unchanged.
- No new mechanism, test framework, model or ACP change; no release, tag or pin.

Issue statement walk:
- 验收措辞另派验证者 → removed; step 3 reuse wording (skills/kaola-project-runner/SKILL.md).
- IDLE_BEFORE_STOP / heartbeat 派出所有合适匹配 → replaced; test-issue-41 asserts new wording and absence of old.
- Delegator/Host/heartbeat 重复职责 & 外层节奏 → heartbeat steps 2–3 aligned with main Skill; Delegator cadence sentence.
- 保留会话身份、授权与并发上限、验收和收尾 → test-issue-118, test-issue-74, test-issue-41 acceptance assertions pass unchanged.
- 使用现有生成和一致性检查，调整过时断言 → render --check PASS, validate.sh rc=0; only test-issue-41 obsolete assertions adjusted.

## Files Changed
templates/orchestrator/SKILL.md.tmpl, templates/orchestrator/references/heartbeat-skeleton.txt, templates/kaola-delegator/SKILL.md.tmpl, scripts/render-skills.py, templates/grok-bot/accepted-revision.json (content stage), tests/contract/test-issue-41-orchestrator.py, CHANGELOG.md, and generated skills/ + hosts/grok-bot/ outputs.

## Test Coverage
tests/contract/test-issue-41-orchestrator.py (updated dispatch assertions: new wording present, "dispatch every suitable match" / "派出所有合适匹配" absent); existing test-issue-118 seat-cap, test-issue-74 delegator, test-issue-49 grok-bot, test-progressive-disclosure (budgets) unchanged and passing.

Acceptance legs:
- automated: `./scripts/validate.sh` rc=0 on 8bf9db2 (/tmp/kpr-189-validate.log) and on final candidate 47cd9f4 (/tmp/kpr-189-validate-final.log; render-skills PASS, grok-bot-verify PASS, residual_pids []). Watchdog rows SKIP by named receipt (bash 3.2.57 < 4, #151).
- manual: Host read-only diff review accepted 8bf9db2.
- unexecuted: live ACP smoke per platform — not applicable (prompt wording only; no transport/adapter change).
- Budgets: main 16904/17408, delegator 4074/4096, heartbeat ref 7583/8192, bridge 2555/2560.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- scripts/render-skills.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-delegator/SKILL.md
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/heartbeat-skeleton.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/grok-bot/accepted-revision.json
- templates/kaola-delegator/SKILL.md.tmpl
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/heartbeat-skeleton.txt
- tests/contract/test-issue-41-orchestrator.py

## Documentation Docking
DOCKED — see .cache/doc-docking.md (CHANGELOG Unreleased entry added; README/AGENTS/docs no impact).

## Follow-Up Items
- None filed. Integration note for Host: #188 (separate worker, branch workflow/issue-188) also edits scripts/render-skills.py (different hunks), templates/grok-bot/accepted-revision.json and hosts/grok-bot/* (identical content-stage change); after both land, rerun render-skills.py --write/--check on the combined tree.
- Delegator Skill has 22 bytes of budget headroom.

## Readiness
READY — accepted by Host; validation pass recorded for candidate hash 1684b5cb…; docked.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-189/.cache/doc-docking.md
- kaola-workflow/archive/issue-189/.cache/final-validation.md
- kaola-workflow/archive/issue-189/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-189/finalization-summary.md
- kaola-workflow/archive/issue-189/mission-ledger.jsonl
- kaola-workflow/archive/issue-189/workflow-state.md
