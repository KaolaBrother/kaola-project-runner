# Documentation docking — issue-135 (candidate b279678)

| File | Status | Evidence |
|---|---|---|
| CHANGELOG.md | updated | `## 0.5.8 — Unreleased` entry: effort id follows the selected model; `reasoning_effort;effort` candidate list; receipt fields `config_application.effort.candidates`/`advertised`, `effective_selection.effort_config_id`; verified cli 2026.09.18-9a7762b |
| docs/api.md | updated | manifest section: per-model option set, `acp_effort_config_id` as ordered `;` candidate list resolved after the model apply, literal-first fallback; receipt section: `effective_selection.effort_config_id` (b279678) |
| templates/references/acp.md.tmpl → skills/*/references/acp.md | rendered | candidate-list sentence naming the receipt fields |
| platforms/cursor-cli.yaml | updated | acp_quirks (model-neutral), acp_verified_versions cli=2026.09.18-9a7762b, acp_effort_config_id |
| README.md | no impact | no effort-config-id or receipt-field description; tier presets unchanged |
| AGENTS.md | no impact | project facts, commands and constraints unchanged |
| templates/SKILL.md.tmpl | no impact | tier presets unchanged (design §7) |
| docs/runner-v2-dual-transport-design-2026-09-11.md | no impact | dated historical design record, not current reference |

DOCKED
