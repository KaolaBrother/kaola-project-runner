# Codex CLI adapter

- Platform ID: `codex`
- Default binary: `codex`
- Binary override: `CODEX_BIN`
- Standalone session prefix: `codex-kaola-<purpose>` (under Project Runner the name is issue-scoped; see SKILL.md)
- Resume: `session/resume`/`session/load` per advertised capability; Continue: the latest `session/list` entry for the canonical cwd
- Runner default preset `codex/default` (`--tier default`): **GPT-6.1 Sol** — `gpt-6.1-sol` with `effort=high`
- Runner astra preset `codex/astra` (`--tier astra`): **GPT-6 Astra** — `gpt-6-astra` with `effort=high`
- Runner luna preset `codex/luna` (`--tier luna`): **GPT-6 Luna** — `gpt-6-luna` with `effort=max`
- Fast support: Codex fast mode via ACP `fast-mode` configId (off/on); explicit off is applied, not assumed

## Preflight

Verify the Codex executable and report optional Kaola Workflow skill or plugin carrier evidence without making Workflow availability a communication gate.

Preflight is read-only: optional Kaola/Workflow surfaces and runtime health are reported as
evidence, and their absence does not block starting the CLI. It never installs, upgrades, adopts,
or rewrites runtime configuration. A requested model absent from or unknown to the readable
catalog is still launched as the exact declared literal, and the catalog fact is reported.

## Launch

ACP runs adapter @agentclientprotocol/codex-acp@2.0.1. The child CLI is the explicit absolute CODEX_PATH binary, else the Runner resolves CODEX_BIN then PATH and sets CODEX_PATH for the adapter (requested Codex CLI 0.160.0). The adapter's nested @openai/codex package does not select that child. ACP start sets mode=agent-full-access after initialize.

Native launch policy, when this adapter supports it, is reported separately from ACP mode
selection. Read the platform permission facts in [acp.md](acp.md); existing explicit policy
and contrary modes take precedence over a managed default.

The Agent decides every action; operate through `"$SKILL_DIR/scripts/runtime-tmux.sh"` as SKILL.md
shows, and read [acp.md](acp.md) before any action that can change the runtime.
