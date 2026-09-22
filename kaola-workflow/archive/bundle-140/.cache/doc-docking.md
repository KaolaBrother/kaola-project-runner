# Documentation docking — bundle-140 (#140)

- CHANGELOG.md — FIXED: 0.5.8 Unreleased entry for #140 (5f1939d).
- docs/api.md — FIXED: optional per-tier `acp_command_default/_upgrade/_alt` manifest fields and the
  argv-carried model receipts (`config_application.model.applied_via: argv`,
  `effective_selection.effective_model_source: launch-argv`, `advertised_model`) (0c879b7).
- templates/references/acp.md.tmpl → skills/*/references/acp.md — FIXED in 9df0d42 (same facts, rendered).
- platforms/devin.yaml acp_quirks → skills/devin-kaola-project-runner/references/acp.md — FIXED in 9df0d42.
- README.md — NO IMPACT: tier CLI surface (`--tier default|upgrade|fable`) and preset ids unchanged; no transport-field list.
- AGENTS.md / architecture docs — NO IMPACT: no architecture or command change.

DOCKED
