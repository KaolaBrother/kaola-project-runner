# Documentation Docking — Issue #192

Status: DOCKED

Checked against `AGENTS.md`'s documentation checklist for the changed public package metadata and consumer reference.

| Surface | Decision | Reason |
|---|---|---|
| `docs/api.md` | Updated | Defines `windows` values and meanings, explains partial confirmed arrays and genuinely unknown periods, distinguishes Factory Standard Usage from Core's separate unspecified Rate Limits, and lists unresolved package IDs with reasons. |
| `templates/orchestrator/references/quota-packages.md` | Updated | Replaces the stale null-until-seeded claim, documents the display rule, and updates Grok/Droid JSON examples to match package CLI output. |
| `skills/kaola-project-runner/references/quota-packages.md` | Regenerated | Rendered copy is byte-identical to the updated template. |
| `platforms/droid.yaml` and `skills/droid-kaola-project-runner/scripts/platform.yaml` | Updated / regenerated | Standard includes its verified 5h, weekly, and monthly windows; Core retains only the owner-confirmed weekly/monthly periods; Extra Usage is an empty window list. |
| `skills/*/scripts/main-skill-build.json` | Regenerated | Build metadata was refreshed by `render-skills.py --write`. |
| `README.md` | No change | No setup, installation, command, or entry-layer behavior changed. |
| `CHANGELOG.md` | No change | This is not a release or version publication; no release notes or restart assertion are appropriate. |
| `AGENTS.md` | No change | Commands, installation guidance, validation policy, constraints, and project architecture are unchanged. |
| `docs/architecture*.md` and `docs/conventions.md` | No change | No architecture, workflow, or release-convention behavior changed. |

The public schema remains `kaola-acp-packages/1`. Documentation states that arrays contain confirmed reset windows; omitted periods are not proven absent when provider documentation is incomplete. The three remaining null package periods have explicit reasons. No quota amounts, reset timestamps, or undocumented Core periods were introduced.
