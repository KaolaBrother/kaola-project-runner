# Documentation Docking — bundle-28 (issue #28)

verdict: DOCKED
candidate: workflow/bundle-28 @ 9923974

## Checked files

- `README.md` — UPDATED: seven-platform table row for Codex CLI
  (`$codex-kaola-project-runner`, `codex`, GPT-5.6 Luna low), quick-use list,
  transport note (pinned ACP command, `--transport pty` argv, default
  `agent-full-access` mapping), seven-platform structure and validation wording.
- `docs/api.md` — UPDATED: seven Skill count, installer targets.
- `docs/architecture.md` — UPDATED: seven-platform template/generated statements.
- `docs/conventions.md` — UPDATED: seven-platform active-Skill statements.
- `AGENTS.md` — UPDATED: managed-region platform counts six→seven.
- `CHANGELOG.md` — UPDATED: Unreleased entry describing issue #28 (pinned ACP
  versions, transports, model/effort defaults, permission mappings, holder
  capability `{}` and nextCursor fixes, CODEX_PATH, no global config).
- `skills/codex-kaola-project-runner/` — GENERATED via render-skills.py --write;
  contains pinned ACP command, model facts, PTY fallback facts, empty-object
  capability quirk, `login requires a PTY: false`.
- `templates/grok-golden/` — NO-IMPACT: frozen; byte-identical (observation
  contract test_10 verifies).
- Historical dated smoke/decision records — NO-IMPACT: retain historical
  five/six-platform wording as dated records.

## No-impact reasons

- `docs/acp-watch/` design records describe the ACP watch surface, unchanged by
  platform registration; codex inherits the same surface through the holder.
