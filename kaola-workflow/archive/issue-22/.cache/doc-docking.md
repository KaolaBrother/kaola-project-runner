# Documentation docking — issue-22 / PR #23

Candidate: `0c03c893cf2cc91d78305362bf28119e2f947471`

## Checked

- `README.md` — added default `start` skip-all paragraph (ACP/PTY knobs, OpenCode ACP gap, `permit` still available, trust/login out of scope).
- `CHANGELOG.md` — Unreleased bullet for issue #22 skip-all knobs, including the review-measured Kimi/Grok flags and OpenCode ACP gap.
- `platforms/*.yaml` `launch_summary` / `acp_command` — source of generated Skill launch text; re-rendered.
- Generated Skills — `./scripts/render-skills.py --check` PASS; no hand-edits.
- `templates/grok-golden/` — empty diff vs `origin/main`.
- `docs/api.md` / architecture docs — no permission-mode default contract; no-impact.
- `AGENTS.md` documentation map — README + CHANGELOG cover the public start behavior.

## Verdict

DOCKED
