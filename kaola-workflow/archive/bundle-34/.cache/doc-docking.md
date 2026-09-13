# Doc docking — bundle-34 (issue #34)

Checked AGENTS.md documentation map against changed public behavior at commit
7226f4d (post-1545404: test-harness-only bash 3.2 array fix — docs unchanged).

| File | Result | Reason |
| --- | --- | --- |
| README.md | DOCKED | Selection precedence, tier presets, and per-platform Fast mechanisms updated (parameterized Cursor ACP, Claude `--settings fastMode`, Codex service_tier, model variants). |
| CHANGELOG.md | DOCKED | Unreleased entry covers presets, explicit precedence, Fast opt-in, Cursor parameterized picker, Claude settings pin, resume-preserved, receipt fields, and no-escalation guarantees. |
| docs/api.md | DOCKED | Manifest field list now documents `acp_init_meta`, `acp_fast_values`, `acp_model_map` decomposition, and the verbatim-settings Fast mechanism. |
| docs/architecture.md | DOCKED | Model-selection section describes tier/effort/Fast resolution, native mechanisms, unsupported reporting, and resume preservation. |
| templates/SKILL.md.tmpl | DOCKED | Fast guidance rewritten for explicit opt-in; per-manifest FAST_SUMMARY renders platform-specific facts. |
| templates/references/acp.md.tmpl | DOCKED | Documents init `_meta` negotiation, ordered config application, decomposition mapping, and truthful fast reporting. |
| platforms/*.yaml | DOCKED | All seven manifests declare default/upgrade presets, fast_support/fast_summary, ACP config IDs, and Cursor-only `acp_init_meta`/`acp_fast_values`/`acp_model_map`. |
| skills/ (generated) | DOCKED | Regenerated via `render-skills.py --write`; `--check` passes — no hand edits. |
| AGENTS.md | DOCKED | No change needed: commands, constraints, and runner contract unchanged by this run. |
| templates/grok-golden/ | DOCKED | Frozen per contract — untouched. |

verdict: DOCKED
