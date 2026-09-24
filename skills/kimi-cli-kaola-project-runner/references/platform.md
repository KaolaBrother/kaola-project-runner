# Kimi CLI adapter

- Platform ID: `kimi-cli`
- Default binary: `kimi`
- Binary override: `KIMI_BIN`
- Standalone session prefix: `kimi-cli-kaola-<purpose>` (under Project Runner the name is issue-scoped; see SKILL.md)
- Resume: `session/resume`/`session/load` per advertised capability; Continue: the latest `session/list` entry for the canonical cwd
- Runner default preset (`--tier default`): **Kimi K3 Max** — `kimi-code/k3` with `thinking=max`
- Runner upgrade preset (`--tier upgrade`): equals default here
- Runner alternative preset (`--tier alternative`): **Kimi K2.8** — `kimi-code/kimi-for-coding` with `thinking=max`
- Fast support: no native Fast toggle; speed-named catalog models such as kimi-code/kimi-for-coding-highspeed are explicit model choices, not a Fast switch

## Preflight

Verify the Kimi executable and report optional Kaola carrier/doctor evidence without gating communication.

Preflight is read-only: optional Kaola/Workflow surfaces and runtime health are reported as
evidence, and their absence does not block starting the CLI. It never installs, upgrades, adopts,
or rewrites runtime configuration. A requested model absent from or unknown to the readable
catalog is still launched as the exact declared literal, and the catalog fact is reported.

## Launch

ACP runs kimi acp; ACP start sets mode=yolo after initialize and applies effort through the ACP thinking config option, whose ladder is low/high/max rather than the five-level KIMI_MODEL_THINKING_EFFORT env ladder (low/medium/high/xhigh/max) -- max is valid on both, but the two sets are not the same. The ACP model currentValue is kimi-code/kimi-for-coding, so the kimi-code/k3 default preset is applied, never inherited, and "Kimi K3 Max" names the composition model=kimi-code/k3 plus thinking=max: the catalog carries no "Max" in any display name.

The Agent decides every action; operate through `"$SKILL_DIR/scripts/runtime-tmux.sh"` as SKILL.md
shows, and read [acp.md](acp.md) before any action that can change the runtime.
