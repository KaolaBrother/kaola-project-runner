# Documentation docking — issue-119

verdict: DOCKED

Checked against the changed public behavior (per-platform Host entry, non-ZCode Host binding, effective_selection receipt, opencode explicit-selection refusal, five new installer runtimes):

- CHANGELOG.md — `## Unreleased` entry added (70d448d). DOCKED.
- README.md — install examples gained `--runtime grok-cli|droid|opencode|kimi-cli` with roots and the matrix pointer (7183b2f); existing pinned sentences untouched. DOCKED.
- docs/api.md — `--runtime` paragraph lists the new destinations and points to host-entry-matrix.md (7183b2f). DOCKED.
- templates/orchestrator/references/host-entry-matrix.md — new reference: entry fact, E1/E2 rules, per-platform matrix, D3 results, OpenCode H2 answers (70d448d, 7f4b794, 2d4936c). DOCKED.
- templates/orchestrator/SKILL.md.tmpl, references/host-startup.md.tmpl, references/heartbeat-skeleton.txt, templates/kaola-delegator/references/handoff.md.tmpl — first-line wording generalized within budget (70d448d). DOCKED.
- scripts/install-local.sh `--help` — new runtimes + `--runtime grok` refusal points at `grok-cli` (70d448d). DOCKED.
- docs/zcode-host.md — no impact: ZCode behavior and carrier are byte-identical.
- docs/architecture.md, docs/conventions.md, docs/codex-host.md, docs/grok-bot-host.md — no impact: no architecture/convention change; codex entry stays empty (#122); Grok Bot unchanged.
- AGENTS.md "Layered entry" still says Kaola-Delegator hands off to one ZCode Host — still true (Delegator unchanged by #119); no edit.
