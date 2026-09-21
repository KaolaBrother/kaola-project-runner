# Documentation docking — issue-124

verdict: DOCKED

Checked against the changed public behavior (grok ACP `start` records `cli_version` in record.json, holder state and the start receipt `transport`; grok `acp_verified_versions` cli 1.0.25 -> 1.0.40):

- CHANGELOG.md — `## Unreleased` entry added (970f546). DOCKED.
- docs/api.md — ACP receipt paragraph gains the `cli_version` sentence (fields `path`, `version`, `verified_versions`; fact only, never a gate) beside the Claude `runtime_binary` description (970f546). DOCKED.
- platforms/grok.yaml `acp_verified_versions` + `steering_summary`, rendered to skills/grok-kaola-project-runner/scripts/platform.yaml and references/steering.md (970f546). DOCKED.
- templates/references/acp.md.tmpl — no impact: it documents receipt bounding, and `cli_version` is a small scalar dict that is never bounded.
- docs/runner-v2-dual-transport-design.md (:367, :392, :468) and docs/poc-acp-transport-2026-09-11.md (:47) — no edit: dated historical measurements on Grok 1.0.25; :367 already specified the `--version` fallback this issue implements.
- README.md, docs/architecture.md, docs/conventions.md, AGENTS.md — no impact: no new command, option, install path, architecture or convention.
