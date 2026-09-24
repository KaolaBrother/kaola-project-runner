# Claude Code adapter

- Platform ID: `claude-code`
- Default binary: `claude`
- Binary override: `CLAUDE_BIN`
- Standalone session prefix: `claude-code-kaola-<purpose>` (under Project Runner the name is issue-scoped; see SKILL.md)
- Resume: `session/resume`/`session/load` per advertised capability; Continue: the latest `session/list` entry for the canonical cwd
- Runner default preset (`--tier default`): **Opus High** — `opus` with `effort=high`
- Runner upgrade preset (`--tier upgrade`): **Fable High** — `fable` with `effort=high`
- Fast support: Fast via process-scoped `--settings '{"fastMode": ...}'` at launch: `--fast on` passes fastMode=true, `--fast off` pins fastMode=false for the session; the native CLI determines model support — effective stays unknown without native evidence and the selected model is never changed

## Preflight

Verify the Claude executable and report optional Kaola carrier and launch-option evidence without gating communication.

Preflight is read-only: optional Kaola/Workflow surfaces and runtime health are reported as
evidence, and their absence does not block starting the CLI. It never installs, upgrades, adopts,
or rewrites runtime configuration. A requested model absent from or unknown to the readable
catalog is still launched as the exact declared literal, and the catalog fact is reported.

## Launch

ACP runs the vendored claude-code-acp bridge (node, Skill-relative dist), which drives the exact claude binary as one subscription subprocess per turn; ACP start sets mode=bypassPermissions after a working initialize.

The Agent decides every action; operate through `"$SKILL_DIR/scripts/runtime-tmux.sh"` as SKILL.md
shows, and read [acp.md](acp.md) before any action that can change the runtime.
