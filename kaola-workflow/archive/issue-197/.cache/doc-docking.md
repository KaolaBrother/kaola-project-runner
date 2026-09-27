# Doc docking — issue-197

Checked against AGENTS.md documentation map and changed public behavior (none: no receipt field, CLI, API, or runtime behavior changed).

- platforms/devin.yaml (acp_quirks) — FIXED: corrected claim that ACP currentValue always stays swe-2-high and that the -medium opus-fusion id was unmeasured; rendered into skills/devin-kaola-project-runner/references/acp.md and scripts/platform.yaml via render-skills.py --write.
- CHANGELOG.md — FIXED: Unreleased entry for #197, notes platforms/devin.yaml changed so the release operator test is non-empty.
- docs/api.md — no impact: already documents config_application.model applied_via argv, effective_model_source launch-argv, advertised_model as the agent's (possibly stale) value, and status/observe reporting currentValue.
- README.md, docs/architecture.md, docs/conventions.md — no impact: no setup, architecture, environment, or validation-command change.
- Generated surfaces (skills/, hosts/grok-bot/) — regenerated only; Grok Bot accepted-revision returned to content stage (release pin is release-transaction work).

DOCKED
