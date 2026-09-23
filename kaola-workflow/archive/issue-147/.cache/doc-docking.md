# Documentation Docking — issue-147

candidate: 77c63cb (workflow/issue-147)

## Checked files
- docs/api.md — UPDATED: full `kaola-acp survey` contract paragraph (argv, login-shell probe, `kaola-acp-survey/1` keys, status/source values, ZCode rule, OpenCode Go note); "only command without --repo" sentence now names survey. Transcribed from the real receipt (survey-narrow-path-77c63cb.json).
- README.md — UPDATED: one sentence beside the ACP session-watching commands.
- templates/references/acp.md.tmpl — UPDATED (+ 10 rendered skills/*/references/acp.md via render-skills.py --write; --check PASS, budgets OK).
- CHANGELOG.md — UPDATED: Unreleased entry for Issue #147.
- docs/acp-watch/list-view.md — NO IMPACT: session-oriented list/view contract; the survey is explicitly not a session list (issue non-goal) and `list` is unchanged.
- docs/architecture.md, docs/conventions.md, docs/README.md — NO IMPACT: no command inventory of kaola-acp host-wide commands.
- AGENTS.md — NO IMPACT: install/test/lint commands unchanged.
- templates/orchestrator/ (main Skill) — NO IMPACT: control-plane dispatch does not consume install facts; budget unchanged.
- templates/kaola-delegator/, hosts/grok-bot/ — NO IMPACT: no change to Delegator or bridge surfaces (render --check PASS).

DOCKED
