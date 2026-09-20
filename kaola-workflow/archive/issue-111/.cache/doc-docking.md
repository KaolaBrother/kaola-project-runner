# Documentation docking — issue #111

Candidate: `workflow/issue-111@d6bd56b`
Checklist source: `AGENTS.md` → Documentation Map.

## Checked files

| File | Changed public behaviour it had to absorb | Outcome |
|---|---|---|
| `docs/api.md` | the manifest field registry gained the `alt_*` group; `--tier` gained a per-platform third value and a typed refusal; Droid's preset paragraph named the retired `auto` default | **fixed** — new field names listed verbatim with the optional/all-or-nothing rule and the `TIER_BLOCK`/`ALT_TIER_LINE` render path; the `--tier` usage line and the preset-precedence paragraph now carry `PLATFORM_TIER` and the `tier-not-declared` refusal; the Droid paragraph rewritten to `kimi-k3` at `reasoning_effort=max` plus the alternative tier. Two verbatim-duplicated lines in the manifest-fields paragraph (a pre-existing defect inside the exact paragraph being edited) removed. |
| `docs/architecture.md` | the one-paragraph statement of tier selection | **fixed** — the third preset and the refuse-by-name rule added to the existing sentence. |
| `README.md` | the user-facing model-selection paragraph, including a Droid exception sentence that said "both tiers remain Auto Model" | **fixed** — third-tier sentence added naming which platforms declare one; the Droid sentence rewritten to Kimi K3 Max / `kimi-k2.7-code`. |
| `CHANGELOG.md` | user-visible change | **fixed** — two entries under a new `## 0.5.5 — unreleased` heading. Left unreleased deliberately: tagging and the Grok Bot `saveable: true` pin are the Host's release step. |
| `platforms/*.yaml` prose (`launch_summary`, `acp_quirks`) | these render into the generated `references/platform.md` and `references/acp.md`, so they are documentation surfaces | **fixed** — the live facts the issue required recorded: Kimi's three-value ACP thinking ladder vs the five-level env ladder and that "Kimi K3 Max" is a composition; Droid's first-class `kimi-k3`, the `-32602` control that makes the two OKs positive evidence, and why the alternative is an analogue carrying no effort; dsh's Runner-side display name vs the bare catalog name and the `deepseek-official/deepseek-flash` name trap; ZCode's provider-qualified backslash spelling, the `thought`/`thoughtLevel` tolerance, the absent `currentValue` at `session/new`, and the pointer to the test that keeps #108 and #111 one source of truth; Devin's catalog name vs the shortened preset name and the absence of an effort option. |
| `skills/**`, `hosts/grok-bot/**` | generated | **regenerated** only via `./scripts/render-skills.py --write`; never hand-edited. `templates/grok-golden/` byte-identical. |
| `docs/zcode-host.md`, `docs/acp-watch/` | inspected | **no impact** — neither describes model presets or the tier vocabulary. |

Every signature, field name, flag, and receipt key above was transcribed from the
changed source, not recalled: the field names from `scripts/render-skills.py` `REQUIRED`,
the refusal shape from a real `kaola-acp.py` receipt, and the Droid values from the
manifest and the passing contract suite.

## Verdict

DOCKED
