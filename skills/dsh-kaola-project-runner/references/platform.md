# dsh adapter

- Platform ID: `dsh`
- Default binary: `dsh`
- Binary override: `DSH_BIN`
- Standalone session prefix: `dsh-kaola-<purpose>` (under Project Runner the name is issue-scoped; see SKILL.md)
- Resume: `session/resume`/`session/load` per advertised capability; Continue: `unsupported`
- Runner default preset (`--tier default`): **DeepSeek V4.1 Flash (OpenCode Go)** — `opencode-go/deepseek-v4.1-flash` with `no Runner effort override`
- Runner upgrade preset (`--tier upgrade`): equals default here
- Fast support: no native Fast toggle and no Fast config option on the ACP surface; the catalog's flash-named routes are explicit model choices, not a Fast switch

## Preflight

Verify the dsh executable, report `dsh --version` and whether an `acp` profile exists under $DSH_HOME, and never write anything under that home.

Preflight is read-only: optional Kaola/Workflow surfaces and runtime health are reported as
evidence, and their absence does not block starting the CLI. It never installs, upgrades, adopts,
or rewrites runtime configuration. A requested model absent from or unknown to the readable
catalog is still launched as the exact declared literal, and the catalog fact is reported.

## Launch

ACP runs dsh --profile acp, the shipped automation-only ACP v1 stdio server; the acp profile takes no application arguments and dsh advertises no ACP mode option, so ACP start sets no mode and launches with DSH_PERMISSION_MODE instead (see SKILL.md). The default preset opencode-go/deepseek-v4.1-flash travels as the acp_model_map wire value ["opencode-go","deepseek-v4.1-flash"]; "DeepSeek V4.1 Flash (OpenCode Go)" is a Runner-side display name, not a catalog string (the catalog shows bare deepseek-v4.1-flash, and deepseek-official/deepseek-flash is a different route). The shipped profile pins deepseek-official, so this default needs its own credentialed provider.

The Agent decides every action; operate through `"$SKILL_DIR/scripts/runtime-tmux.sh"` as SKILL.md
shows, and read [acp.md](acp.md) before any action that can change the runtime.
