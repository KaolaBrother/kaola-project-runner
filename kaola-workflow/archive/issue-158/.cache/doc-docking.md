# Documentation docking — issue-158 (candidate e6e4cc9)

Checked against the frozen candidate's real behavior:

- docs/api.md — no impact: already documents `--permission-mode` as the Agent-facing start flag; no line quotes the dsh refusal text.
- README.md, AGENTS.md, docs/architecture.md, docs/conventions.md — no impact: no statement of the dsh refusal wording (grep "must be one of" / "mode for dsh" → 0 hits).
- CHANGELOG.md — no impact: refusal message wording only; the flag, value set, and forwarding contract are unchanged, and the Host scoped delivery to one accepted commit.
- templates/, hosts/grok-bot/, templates/grok-golden/ — untouched (scripts/kaola-acp.py is vendored into skills/*/scripts/ by the renderer only).

Status: DOCKED
