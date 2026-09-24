# Droid adapter

- Platform ID: `droid`
- Default binary: `droid`
- Binary override: `DROID_BIN`
- Standalone session prefix: `droid-kaola-<purpose>` (under Project Runner the name is issue-scoped; see SKILL.md)
- Resume: `session/resume`/`session/load` per advertised capability; Continue: the latest `session/list` entry for the canonical cwd
- Runner default preset (`--tier default`): **Auto Model** — `auto` with `no Runner effort override`
- Runner upgrade preset (`--tier upgrade`): equals default here
- Runner core preset (`--tier core`): **Kimi K3 Max** — `kimi-k3` with `reasoning_effort=max`
- Fast support: no separate Fast toggle; `-fast` catalog ids are explicit `--model` choices

## Preflight

Verify the droid executable, report `droid --version` and read-only native settings facts (~/.factory/settings.json model/reasoningEffort) without gating communication.

Preflight is read-only: optional Kaola/Workflow surfaces and runtime health are reported as
evidence, and their absence does not block starting the CLI. It never installs, upgrades, adopts,
or rewrites runtime configuration. A requested model absent from or unknown to the readable
catalog is still launched as the exact declared literal, and the catalog fact is reported.

## Launch

ACP runs the native droid exec --output-format acp agent; ACP start applies the resolved model and autonomy_level=auto-high after initialize/session-new (the default ACP session is already auto-high; the native default model currentValue is not auto, so the preset model is applied explicitly, never inherited). The default preset is the first-class catalog id auto with no effort pin, and --tier upgrade is the same auto preset because no stronger Droid tier is established; --tier core is the first-class catalog id kimi-k3 at reasoning_effort=max, a separate tier below the default -- auto and kimi-k3 at max were both accepted live on 0.220.0, so no acp_model_map entry is needed.

The Agent decides every action; operate through `"$SKILL_DIR/scripts/runtime-tmux.sh"` as SKILL.md
shows, and read [acp.md](acp.md) before any action that can change the runtime.
