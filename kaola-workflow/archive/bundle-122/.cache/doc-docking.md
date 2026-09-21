# Documentation docking — bundle-122 (#122), candidate beb8a04

Checked against AGENTS.md documentation map:
- templates/orchestrator/references/host-entry-matrix.md — FIXED: deferred "until it is made" paragraph replaced by the decided fail-closed rule; codex row names `host-entry-unsupported`. Rendered copy in skills/kaola-project-runner/references/.
- templates/orchestrator/references/host-startup.md.tmpl — FIXED: empty entry cannot host and refuses `host-entry-unsupported`.
- docs/api.md — FIXED: `dispatcher-no-carrier` meaning + the three refusals.
- docs/zcode-host.md — FIXED: explicit-target and entry-less dispatcher wording.
- CHANGELOG.md — FIXED: Unreleased entry for #122.
- templates/orchestrator/SKILL.md.tmpl (main Skill) — no change: already links host-entry-matrix.md; budget 17393/17408 B.
- README.md — no impact: no Host-admission or dispatcher-row wording (checked by grep for dispatcher-no-carrier / entry-less).
- templates/kaola-delegator/, hosts/grok-bot/ — no impact: Delegator starts a ZCode Host (has an entry).
- templates/grok-golden/ — frozen, untouched.

DOCKED
