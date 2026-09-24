# Codex CLI adapter

- Platform ID: `codex`
- Default binary: `codex`
- Binary override: `CODEX_BIN`
- Standalone session prefix: `codex-kaola-<purpose>` (under Project Runner the name is issue-scoped; see SKILL.md)
- Resume: `session/resume`/`session/load` per advertised capability; Continue: the latest `session/list` entry for the canonical cwd
- Runner default preset (`--tier default`): **GPT-6 Sol High** — `gpt-6-sol` with `effort=high`
- Runner upgrade preset (`--tier upgrade`): **GPT-6 Astra High** — `gpt-6-astra` with `effort=high`
- Fast support: Codex fast mode via ACP `fast-mode` configId (off/on); explicit off is applied, not assumed

## Preflight

Verify the Codex executable and report optional Kaola Workflow skill or plugin carrier evidence without making Workflow availability a communication gate.

Preflight is read-only: optional Kaola/Workflow surfaces and runtime health are reported as
evidence, and their absence does not block starting the CLI. It never installs, upgrades, adopts,
or rewrites runtime configuration. A requested model absent from or unknown to the readable
catalog is still launched as the exact declared literal, and the catalog fact is reported.

## Launch

ACP runs the pinned npx codex-acp wrapper (@openai/codex plus @agentclientprotocol/codex-acp); ACP start sets mode=agent-full-access after initialize.

The Agent decides every action; operate through `"$SKILL_DIR/scripts/runtime-tmux.sh"` as SKILL.md
shows, and read [acp.md](acp.md) before any action that can change the runtime.
