# Finalization Summary — issue-188

## Delivered
Issue #188 (Use runtime-specific named model presets; retire universal upgrade tiers), accepted by Host on frozen candidate ca1a2fafdef6af44afa029acc337b7f21fd8840e (merge of main 9106b9d / #189 sink included).
- Only `--tier default` is common. Each manifest lists its own words in `named_tiers`, each with `<w>_model_{name,id,parameters,effort}`; fixed default/upgrade/alt slots and `alt_tier_label` removed, no alias, no fallback.
- Presets per the issue table: Claude Code fable/sonnet; Codex astra/luna; Cursor opus (claude-opus-5-5-high); Devin opus-fusion/fable with per-preset launch `--model` kept (`acp_command_<w>`); Droid new opus (claude-opus-5-5, reasoning_effort=high) plus existing core; Kimi kimi-k2-8 (was alternative); dsh/Grok/OpenCode/ZCode default only.
- Defaults, model IDs, effort, Fast, explicit --model/--effort precedence unchanged; display names drop the effort suffix (effort shown separately).
- kaola-acp.py: declared_tiers drives tier_declared/tier_prefix and the existing typed `tier-not-declared` refusal; drain-restart refuses a recorded undeclared tier (retired `upgrade`/`alternative`) before the stop instead of resolving to default; live seats are not restarted.
- Renderer tier blocks, worker SKILL.md.tmpl, platform.md.tmpl, adapters (ADAPTER_NAMED_TIERS / ADAPTER_<W>_MODEL_*), orchestrator "Other tiers" row, generated Skills.
- No new classification/policy engine, dedicated model tests, catalog/price probes, release, tag or pin.

Issue statement walk:
- 十平台准确表达上表；无 upgrade、无别名/排序 → platforms/*.yaml + generated platform.md preset lines; test-issue-111 pins named tiers per platform and asserts generated Skills list exactly the declared tiers and no `--tier upgrade`.
- 未知名称继续通过既有错误机制报告 → tier_refusal unchanged in shape; test-issue-111 (opencode `--tier upgrade` refused, devin/droid refusals list new available_tiers); test-droid-acp-contract retired upgrade refused with no config events.
- 既有模型/effort/Fast/显式参数优先级/传输不变；在途会话不重启；旧记录不静默降级 → model IDs/efforts byte-equal to prior presets; resolve_selection precedence code untouched; drain-restart recorded-tier refusal before stop.
- 通过 renderer 更新生成文件，预算/冻结/pin 约束 → render --check PASS, budgets OK (main 16985/17408), grok-golden untouched, hosts/grok-bot identical to main, no pin.
- README 十平台表与说明 → README model-selection chapter (see doc-docking).
- 现有验证，仅调整过时断言，不加专用测试 → six existing test files adjusted; no new test file or mechanism.
- #189 独立 → merged cleanly; scheduling wording intact (test-issue-41 PASS).

## Files Changed
platforms/*.yaml (10), scripts/adapters/*.sh (10), scripts/kaola-acp.py, scripts/kaola-tmux.sh, scripts/render-skills.py (tier blocks), templates/SKILL.md.tmpl, templates/references/platform.md.tmpl, templates/orchestrator/SKILL.md.tmpl, README.md, docs/api.md, docs/architecture.md, CHANGELOG.md, six tests/contract files, generated skills/.

## Test Coverage
Adjusted existing assertions only: test-issue-111-model-tiers (named-tier shape), test-acp-contract (codex astra, cursor opus), test-droid-acp-contract (opus/core available tiers; upgrade refused), test-issue-130-pty-retired (resume with astra), test-issue-50-runner-integration (fable), test-generated-skills (leakage exemptions for renamed display names and Droid claude-opus-5-5).

Acceptance legs:
- automated: `./scripts/render-skills.py --check` rc=0 and `./scripts/validate.sh` rc=0 in 561 s, foreground, on ca1a2fa (/tmp/kpr-188-validate-4.log, 823 lines, 0 FAIL/ERROR, residual_pids []); HEAD unchanged and tree clean before/after. Named prerequisite skips: 2 TestValidateWatchdog rows (bash 3.2.57 < 4, #151). Earlier run /tmp/kpr-188-validate-3.log was Terminated: 15 without rc and is not evidence.
- manual: Host acceptance of ca1a2fa on 2026-09-27.
- unexecuted: live ACP smoke per platform and live model acceptance — not run; the issue excludes catalog/live acceptance as a preset gate and transport is unchanged.

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
- docs/architecture.md
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
- scripts/adapters/claude-code.sh
- scripts/adapters/codex.sh
- scripts/adapters/cursor-cli.sh
- scripts/adapters/devin.sh
- scripts/adapters/droid.sh
- scripts/adapters/dsh.sh
- scripts/adapters/grok.sh
- scripts/adapters/kimi-cli.sh
- scripts/adapters/opencode.sh
- scripts/adapters/zcode.sh
- scripts/kaola-acp.py
- scripts/kaola-tmux.sh
- scripts/render-skills.py
- skills/claude-code-kaola-project-runner/SKILL.md
- skills/claude-code-kaola-project-runner/references/platform.md
- skills/claude-code-kaola-project-runner/scripts/adapters/claude-code.sh
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-tmux.sh
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/platform.yaml
- skills/codex-kaola-project-runner/SKILL.md
- skills/codex-kaola-project-runner/references/platform.md
- skills/codex-kaola-project-runner/scripts/adapters/codex.sh
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-tmux.sh
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/platform.yaml
- skills/cursor-cli-kaola-project-runner/SKILL.md
- skills/cursor-cli-kaola-project-runner/references/acp.md
- skills/cursor-cli-kaola-project-runner/references/platform.md
- skills/cursor-cli-kaola-project-runner/scripts/adapters/cursor-cli.sh
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-tmux.sh
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/platform.yaml
- skills/devin-kaola-project-runner/SKILL.md
- skills/devin-kaola-project-runner/references/acp.md
- skills/devin-kaola-project-runner/references/platform.md
- skills/devin-kaola-project-runner/scripts/adapters/devin.sh
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-tmux.sh
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/platform.yaml
- skills/droid-kaola-project-runner/SKILL.md
- skills/droid-kaola-project-runner/references/platform.md
- skills/droid-kaola-project-runner/scripts/adapters/droid.sh
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-tmux.sh
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/platform.yaml
- skills/dsh-kaola-project-runner/SKILL.md
- skills/dsh-kaola-project-runner/references/platform.md
- skills/dsh-kaola-project-runner/scripts/adapters/dsh.sh
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-tmux.sh
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/platform.yaml
- skills/grok-kaola-project-runner/SKILL.md
- skills/grok-kaola-project-runner/references/platform.md
- skills/grok-kaola-project-runner/scripts/adapters/grok.sh
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-tmux.sh
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/platform.yaml
- skills/kaola-project-runner/SKILL.md
- skills/kimi-cli-kaola-project-runner/SKILL.md
- skills/kimi-cli-kaola-project-runner/references/platform.md
- skills/kimi-cli-kaola-project-runner/scripts/adapters/kimi-cli.sh
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-tmux.sh
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/kimi-cli-kaola-project-runner/scripts/platform.yaml
- skills/opencode-kaola-project-runner/SKILL.md
- skills/opencode-kaola-project-runner/references/platform.md
- skills/opencode-kaola-project-runner/scripts/adapters/opencode.sh
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-tmux.sh
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/platform.yaml
- skills/zcode-kaola-project-runner/SKILL.md
- skills/zcode-kaola-project-runner/references/acp.md
- skills/zcode-kaola-project-runner/references/platform.md
- skills/zcode-kaola-project-runner/scripts/adapters/zcode.sh
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-tmux.sh
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/platform.yaml
- templates/SKILL.md.tmpl
- templates/orchestrator/SKILL.md.tmpl
- templates/references/platform.md.tmpl
- tests/contract/test-acp-contract.py
- tests/contract/test-droid-acp-contract.py
- tests/contract/test-generated-skills.py
- tests/contract/test-issue-111-model-tiers.py
- tests/contract/test-issue-130-pty-retired.py
- tests/contract/test-issue-50-runner-integration.py

## Documentation Docking
DOCKED — see .cache/doc-docking.md.

## Follow-Up Items
- None filed. Notes for Host: main Skill budget headroom is 423 B (16985/17408). Running seats whose record carries tier `upgrade`/`alternative` keep running; a later drain-restart must pass a declared `--tier`. Next release assessment: operator diff is non-empty (every platforms/*.yaml and scripts/adapters/*.sh). #190 builds on this baseline and is not started here.

## Readiness
READY — accepted by Host; validation pass recorded for candidate hash b2654cb5…; docked.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-188/.cache/doc-docking.md
- kaola-workflow/archive/issue-188/.cache/final-validation.md
- kaola-workflow/archive/issue-188/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-188/finalization-summary.md
- kaola-workflow/archive/issue-188/mission-ledger.jsonl
- kaola-workflow/archive/issue-188/workflow-state.md
