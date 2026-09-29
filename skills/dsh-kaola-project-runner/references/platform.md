# dsh adapter

- Platform ID: `dsh`
- Default binary: `dsh`
- Binary override: `DSH_BIN`
- Standalone session prefix: `dsh-kaola-<purpose>` (under Project Runner the name is issue-scoped; see SKILL.md)
- Resume: `session/resume`/`session/load` per advertised capability; Continue: `unsupported`
- Runner default preset `dsh/default` (`--tier default`): **DeepSeek V4.1 Flash** — `opencode-go/deepseek-v4.1-flash` with `no Runner effort override`
- Fast support: no native Fast toggle and no Fast config option on the ACP surface; the catalog's flash-named routes are explicit model choices, not a Fast switch

## Preflight

Verify the dsh executable, report `dsh --version` and whether an `acp` profile exists under $DSH_HOME, and never write anything under that home.

Preflight is read-only: optional Kaola/Workflow surfaces and runtime health are reported as
evidence, and their absence does not block starting the CLI. It never installs, upgrades, adopts,
or rewrites runtime configuration. A requested model absent from or unknown to the readable
catalog is still launched as the exact declared literal, and the catalog fact is reported.

## Launch

ACP runs dsh --profile acp, the shipped automation-only ACP v1 stdio server; the acp profile takes no application arguments and dsh advertises no ACP mode option, so ACP start sets no mode and launches with DSH_PERMISSION_MODE instead (see SKILL.md). The default preset opencode-go/deepseek-v4.1-flash travels as the acp_model_map wire value ["opencode-go","deepseek-v4.1-flash"]; "DeepSeek V4.1 Flash" is a Runner-side display name, not a catalog string or the OpenCode Go package display name (the catalog shows bare deepseek-v4.1-flash, and deepseek-official/deepseek-flash is a different route). The shipped profile pins deepseek-official, so this default needs its own credentialed provider. dsh 0.1.7-rc.2 is verified only on this condition: stock, the default cannot run, because the stock opencode-go catalog lists no deepseek-v4.1-flash (set_config_option answers -32602 and the receipt reports the seat still on deepseek-official/deepseek-v4-flash) and stock requests carry no x-opencode-session header (OpenCode Go answers 400 MissingSessionID). Operator recovery, never done by the Runner: in $DSH_HOME/profiles/acp/cordis.patch.yml add one `- id: llm-pi-ai` entry whose `config.providers.opencode-go` sets `apiKeyEnv: OPENCODE_GO_API_KEY`, `api: openai-completions`, `baseURL` copied from an openai-completions entry of pi-ai's providers/data/opencode-go.json, `headers: {x-opencode-session: <operator value>}`, and `models: [{id: deepseek-v4.1-flash, contextWindow: 1000000, maxTokens: 384000, input: [text, image], compat: {thinkingFormat: deepseek, requiresReasoningContentOnAssistantMessages: true, maxTokensField: max_tokens, supportsStore: false, supportsDeveloperRole: false}}]`. That models list replaces the route's whole stock catalog and the static header is shared by every session. Prove it in a throwaway DSH_HOME first: `start`, then check the start receipt's `config_application.model` is applied and `observe`/`status` shows the model `currentValue` ["opencode-go","deepseek-v4.1-flash"], then ONE `send`; preflight's catalog probe is `--version` only and is not this check. dsh 0.1.7 renames $DSH_HOME/settings.yaml to settings.yaml.imported on the first boot of any profile and imports it into that profile only, so keep the route in the acp profile patch.

The Agent decides every action; operate through `"$SKILL_DIR/scripts/runtime-tmux.sh"` as SKILL.md
shows, and read [acp.md](acp.md) before any action that can change the runtime.
