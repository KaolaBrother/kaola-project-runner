# Hermes Agent adapter

- Platform ID: `hermes`
- Default binary: `hermes`
- Binary override: `HERMES_BIN`
- Standalone session prefix: `hermes-kaola-<purpose>` (under Project Runner the name is issue-scoped; see SKILL.md)
- Resume: `session/resume`/`session/load` per advertised capability; Continue: `unsupported`
- Runner default preset `hermes/default` (`--tier default`): **DeepSeek V4.1 Flash 1017** — `deepseek/deepseek-flash` with `effort=high (native reasoning_effort exists on 0.22.6; the adapter does not surface it)`
- Runner max preset `hermes/max` (`--tier max`): **DeepSeek V4.1 Flash 1017** — `deepseek/deepseek-flash` with `effort=max (native reasoning_effort exists on 0.22.6; the adapter does not surface it)`
- Fast support: no native Fast toggle and no Fast config option on the ACP surface (MacBook 0.22.6; 0.22.6 has a native reasoning_effort option but the adapter does not surface it)

## Preflight

Verify the hermes executable, report `hermes --version` and, without gating, the result of `hermes acp --check`; never run `--setup` or `--setup-browser`, never read `~/.hermes/.env`, and never write anything under $HERMES_HOME (default ~/.hermes).

Preflight is read-only: optional Kaola/Workflow surfaces and runtime health are reported as
evidence, and their absence does not block starting the CLI. It never installs, upgrades, adopts,
or rewrites runtime configuration. A requested model absent from or unknown to the readable
catalog is still launched as the exact declared literal, and the catalog fact is reported.

## Launch

The local ACP adapter runs the exact HERMES_BIN as one `hermes --yolo acp` stdio child per ACP holder (`--accept-hooks` is never passed and the caller's HERMES_YOLO_MODE/HERMES_ACCEPT_HOOKS are stripped from its environment). The adapter synthesizes the `model` and `mode` select configOptions from the session/new, load and fork `models`/`modes` blocks, turns `session/set_config_option` for them into `session/set_model`/`session/set_mode`, surfaces the real Hermes error, and refuses any other configId locally. On 0.22.6 the runtime also sends its own native configOptions on that reply; the adapter replaces them with the synthesized list, while a native `config_option_update` notification is forwarded unchanged (see `acp_quirks`). Resume is `session/load`: the adapter removes `resume` from `sessionCapabilities` and turns any `session/resume` it still receives into `session/load`, refusing a null or mismatched result so a silent fresh session is never reported as resumed. Effort comes from Hermes config; 0.22.6 adds a native `reasoning_effort` config option that the adapter does not surface. An ACP child exit is not proof the gateway-owned session ended. MacBook 2026-10-28 exact stop left residual_pids empty and the record stopped, and a later session/load of the same id still attached. Mini and Studio run 0.22.6 but were not driven through a live ACP session.

Native launch policy, when this adapter supports it, is reported separately from ACP mode
selection. Read the platform permission facts in [acp.md](acp.md); existing explicit policy
and contrary modes take precedence over a managed default.

The Agent decides every action; operate through `"$SKILL_DIR/scripts/runtime-tmux.sh"` as SKILL.md
shows, and read [acp.md](acp.md) before any action that can change the runtime.
