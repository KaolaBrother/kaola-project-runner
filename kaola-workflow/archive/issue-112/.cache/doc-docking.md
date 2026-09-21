# Documentation docking — issue-112 (candidate 9708980)

Changed public behaviour:
- The OpenCode PTY launch line is now `opencode <repo> --auto`.
- Top-level `--model`/`--variant` are no longer passed.
- The opencode child gets the loopback proxy bypass on both transports.
- Preflight `loopback=direct|excluded|ensured`.
- `acp_verified_versions cli=2.0.11`.
- V2 TUI chrome detection.

| file | status |
|---|---|
| CHANGELOG.md | UPDATED: 0.5.5 entry covers both commits (V2 facts + child-scoped injection) |
| docs/api.md | UPDATED: steering calibration names `acp_verified_versions` 2.0.11 |
| platforms/opencode.yaml (renders into skills/opencode-kaola-project-runner/references/{acp,platform,steering}.md) | UPDATED: launch_summary, preflight_summary, acp_quirks, acp_verified_versions, acp_env_allowlist, steering_summary; rendered via render-skills.py --write, --check PASS |
| README.md | NO IMPACT: 15 OpenCode mentions checked. The example usage (L445-456) is transport-generic and still valid. "OpenCode's default ACP path has none at all" (L502/506) is still true, now by 2.0.11 measurement. |
| docs/architecture.md | NO IMPACT: platform lists only (L90, L206) |
| docs/runner-v2-dual-transport-design.md | NO IMPACT: dated design record |
| docs/acp-live-verification-2026-09-11.md, docs/live-smoke-*.md | NO IMPACT: dated historical evidence (the 1.18.29 line is a record of that date, not a current claim) |
| AGENTS.md / CLAUDE.md | NO IMPACT: no OpenCode-specific facts |

DOCKED
