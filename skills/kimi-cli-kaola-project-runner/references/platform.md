# Kimi CLI adapter

- Platform ID: `kimi-cli`
- Default binary: `kimi`
- Binary override: `KIMI_BIN`
- Standalone session prefix: `kimi-cli-kaola-<purpose>` (under Project Runner the name is issue-scoped; see SKILL.md)
- Resume: `session/resume`/`session/load` per advertised capability; Continue: the latest `session/list` entry for the canonical cwd
- Runner default preset `kimi-cli/default` (`--tier default`): **Kimi K2.8** — `kimi-code/kimi-for-coding` with `thinking=max`
- Runner kimi-k3-1-pro preset `kimi-cli/kimi-k3-1-pro` (`--tier kimi-k3-1-pro`): **Kimi K3.1 Pro** — `kimi-code/k3.1-pro` with `thinking=max`
- Fast support: no native Fast toggle; speed-named catalog models such as kimi-code/kimi-for-coding-highspeed are explicit model choices, not a Fast switch

## Preflight

Verify the Kimi executable and report optional Kaola carrier/doctor evidence without gating communication.

Preflight is read-only: optional Kaola/Workflow surfaces and runtime health are reported as
evidence, and their absence does not block starting the CLI. It never installs, upgrades, adopts,
or rewrites runtime configuration. A requested model absent from or unknown to the readable
catalog is still launched as the exact declared literal, and the catalog fact is reported.

## Launch

ACP runs kimi acp; ACP start sets mode=yolo after initialize and applies effort through the ACP thinking config option, whose ladder is low/high/max rather than the five-level KIMI_MODEL_THINKING_EFFORT env ladder (low/medium/high/xhigh/max) -- max is valid on both, but the two sets are not the same. The selected preset's model and thinking are applied explicitly at start and never inherited from the ACP current value: default is model=kimi-code/kimi-for-coding plus thinking=max, and --tier kimi-k3-1-pro pins kimi-code/k3.1-pro (the catalog carries no "Max" in any display name).

Native launch policy, when this adapter supports it, is reported separately from ACP mode
selection. Read the platform permission facts in [acp.md](acp.md); existing explicit policy
and contrary modes take precedence over a managed default.

The Agent decides every action; operate through `"$SKILL_DIR/scripts/runtime-tmux.sh"` as SKILL.md
shows, and read [acp.md](acp.md) before any action that can change the runtime.
