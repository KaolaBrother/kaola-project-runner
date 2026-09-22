# Documentation docking — issue-130 (candidate 84b5938, tree 42db26ad)

Checked against changed public behavior (ACP-only Runner, transport-pty-retired refusal,
default_transport removed, relay/observation removed, #104 PTY reason absorbed):

- README.md — DOCKED (ACP-only transport text, table "Default transport" column dropped; merge
  with #133 keeps the ACP-only diagram and the Mission ledger wording)
- AGENTS.md — DOCKED (snapshot/architecture/security/validation lines ACP-only)
- CHANGELOG.md — DOCKED (Unreleased breaking #130 entry incl. five declared losses + migration;
  #133 entry kept after it)
- docs/api.md, docs/architecture.md, docs/conventions.md, docs/zcode-host.md, docs/README.md,
  docs/acp-watch/README.md, docs/acp-watch/list-view.md — DOCKED (see docs-handback.md classes 1-8)
- docs/runner-v2-dual-transport-design.md → docs/runner-v2-dual-transport-design-2026-09-11.md —
  DOCKED (git mv + one Superseded-by-#130 line)
- Generated skills/ + hosts/grok-bot — DOCKED via render-skills --write/--check rc=0; hosts zero diff
- Setup/install commands, environment — no impact beyond the CHANGELOG migration note
  (reinstall roots after merge; stop PTY sessions with the old build)

Known wording follow-ups (non-blocking, review L3/info): "outbound text is redacted" in AGENTS.md
and the worker template is only implemented in kaola-zcode-acp.py; residual "default transport"
wording in templates/orchestrator/SKILL.md.tmpl; README "forcing PTY".

DOCKED
