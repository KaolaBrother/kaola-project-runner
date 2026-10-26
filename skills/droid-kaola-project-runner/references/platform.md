# Droid adapter

- Platform ID: `droid`
- Default binary: `droid`
- Binary override: `DROID_BIN`
- Standalone session prefix: `droid-kaola-<purpose>` (under Project Runner the name is issue-scoped; see SKILL.md)
- Resume: `session/resume`/`session/load` per advertised capability; Continue: the latest `session/list` entry for the canonical cwd
- Runner default preset `droid/default` (`--tier default`): **Auto Model** — `auto` with `no Runner effort override`
- Runner opus preset `droid/opus` (`--tier opus`): **Opus 5.5** — `claude-opus-5-5` with `reasoning_effort=high`
- Runner core preset `droid/core` (`--tier core`): **DeepSeek V4.1 Flash 1017** — `deepseek-v4.1-flash-1017` with `reasoning_effort=max`
- Fast support: no separate Fast toggle; `-fast` catalog ids are explicit `--model` choices

## Preflight

Verify the droid executable, report `droid --version` and read-only native settings facts (~/.factory/settings.json model/reasoningEffort) without gating communication.

Preflight is read-only: optional Kaola/Workflow surfaces and runtime health are reported as
evidence, and their absence does not block starting the CLI. It never installs, upgrades, adopts,
or rewrites runtime configuration. A requested model absent from or unknown to the readable
catalog is still launched as the exact declared literal, and the catalog fact is reported.

## Launch

ACP runs the native droid exec --output-format acp agent; ACP start applies the resolved model and autonomy_level=auto-high after initialize/session-new (the default ACP session is already auto-high; the native default model currentValue is not auto, so the preset model is applied explicitly, never inherited). The default preset is the first-class catalog id auto with no effort pin; --tier opus is claude-opus-5-5 at reasoning_effort=high and --tier core is the catalog id deepseek-v4.1-flash-1017 (DeepSeek V4.1 Flash 1017, billingPool core) at reasoning_effort=max -- auto was accepted live on 0.220.0; deepseek-v4.1-flash-1017 is a feature-flagged entry of the 0.249.0 catalog that the 0.241.1 CLI rejects and is not yet live-verified, and no acp_model_map entry is declared.

Native launch policy, when this adapter supports it, is reported separately from ACP mode
selection. Read the platform permission facts in [acp.md](acp.md); existing explicit policy
and contrary modes take precedence over a managed default.

The Agent decides every action; operate through `"$SKILL_DIR/scripts/runtime-tmux.sh"` as SKILL.md
shows, and read [acp.md](acp.md) before any action that can change the runtime.
