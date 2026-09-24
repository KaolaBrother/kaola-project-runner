# ZCode adapter

- Platform ID: `zcode`
- Default binary: `zcode`
- Binary override: `ZCODE_BIN`
- Standalone session prefix: `zcode-kaola-<purpose>` (under Project Runner the name is issue-scoped; see SKILL.md)
- Resume: `session/resume`/`session/load` per advertised capability; Continue: the latest `session/list` entry for the canonical cwd
- Runner default preset (`--tier default`): **GLM 5.3 Max** — `GLM-5.3` with `thought=max`
- Runner upgrade preset (`--tier upgrade`): equals default here
- Fast support: no native Fast toggle; thought level is a separate config option (low/high/max)

## Preflight

Verify the explicit ZCode runtime path and report app-server readiness and Coding Plan provider facts without PATH discovery; the bundled runtime ships no terminal UI.

Preflight is read-only: optional Kaola/Workflow surfaces and runtime health are reported as
evidence, and their absence does not block starting the CLI. It never installs, upgrades, adopts,
or rewrites runtime configuration. A requested model absent from or unknown to the readable
catalog is still launched as the exact declared literal, and the catalog fact is reported.

## Launch

ACP runs Skill-relative kaola-zcode-acp.py over the installed ZCode app-server --stdio, from explicit KAOLA_ZCODE_ENTRY and KAOLA_ZCODE_NODE (or ZCODE_BIN); ACP start sets mode=yolo after initialize. The adapter reads the desktop provider registry (~/.zcode/v2/config.json) read-only and selects the enabled GLM Coding Plan provider (Start Plan and pay-as-you-go refused). Because the shipped 3.12.x entry cannot locate its own bundled provider table, the adapter resolves that table next to the verified entry and injects both ZCODE_BUILTIN_PROVIDER_CONFIG_FILE and ZCODE_PERSONAL_PROVIDER_CONFIG_FILE (both or neither, never inherited). On 3.12+ it registers the plan through provider/updateAccountConfig, creates the session with no model channel, selects the model on the account:* provider through session/setModel with persistAsWorkspaceLastUsed false, and answers interaction/requestProviderRuntimeHeaders per model request; a pre-3.12 app-server keeps the in-memory runtimeModel overlay, chosen by that backend's own error rather than a version gate. It never writes ~/.zcode/cli/config.json, never injects auth env, and never logs the plan credential.

The Agent decides every action; operate through `"$SKILL_DIR/scripts/runtime-tmux.sh"` as SKILL.md
shows, and read [acp.md](acp.md) before any action that can change the runtime.
