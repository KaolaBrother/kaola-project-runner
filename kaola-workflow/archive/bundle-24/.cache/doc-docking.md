# Documentation docking — issue #24

Candidate: `4b031ad51a85850960eb24818185f53add72fbb5`

## Checked

- `README.md` — OpenCode default ACP has no skip argv; `--auto` is PTY-only via `--transport pty`.
- `CHANGELOG.md` — Unreleased issue #24 bullet: ACP stays `opencode acp`; PTY `--auto` via `--transport pty` is the bypass; no auto-permit / `OPENCODE_PERMISSION` skip.
- `platforms/opencode.yaml` `acp_quirks` / `launch_summary` — Agent-facing source; re-rendered. Launch first sentence is PTY argv without `--transport pty`; bypass named in the following sentence. `default_transport` remains `acp`.
- Generated OpenCode Skill (`SKILL.md`, `references/acp.md`, `references/platform.md`, `scripts/platform.yaml`) — `./scripts/render-skills.py --check` PASS; no hand-edits.
- `templates/grok-golden/` — empty diff vs `2ede8a8` / this candidate.
- `docs/api.md` — `acp_quirks` already listed as a transport field; no API signature change. No-impact.
- `docs/architecture.md` — no skip-all / OpenCode ACP permission contract. No-impact.
- `AGENTS.md` documentation map — README + CHANGELOG cover the public start behavior.

## Verdict

DOCKED
