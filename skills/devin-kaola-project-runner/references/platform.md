# Devin CLI adapter

- Platform ID: `devin`
- Default binary: `devin`
- Binary override: `DEVIN_BIN`
- Standalone session prefix: `devin-kaola-<purpose>` (under Project Runner the name is issue-scoped; see SKILL.md)
- Resume: `session/resume`/`session/load` per advertised capability; Continue: the latest `session/list` entry for the canonical cwd
- Runner default preset (`--tier default`): **SWE-2 Max** — `swe-2-max` with `effort=max (encoded in model ID)`
- Runner upgrade preset (`--tier upgrade`): **Fusion High (Opus 5.5 High + SWE-2 Medium)** — `fusion-claude-opus-5-5-high-sidekick-swe-2-medium` with `effort=high (encoded in model ID)`
- Runner fable preset (`--tier fable`): **Fusion High (Fable 5.1 High + SWE-2 Medium)** — `fusion-claude-fable-5-1-high-sidekick-swe-2-medium` with `effort=high (encoded in model ID)`
- Fast support: Fast via catalog `-fast`/`-priority` model variants only when the resolved model advertises one; preset models have no fast variant

## Preflight

Verify the Devin executable and report optional Kaola carrier and skill evidence without gating communication.

Preflight is read-only: optional Kaola/Workflow surfaces and runtime health are reported as
evidence, and their absence does not block starting the CLI. It never installs, upgrades, adopts,
or rewrites runtime configuration. A requested model absent from or unknown to the readable
catalog is still launched as the exact declared literal, and the catalog fact is reported.

## Launch

ACP runs devin acp, each tier spawned with its preset --model (acp_command_<tier>, Issue #140); ACP start sets mode=bypass after initialize.

The Agent decides every action; operate through `"$SKILL_DIR/scripts/runtime-tmux.sh"` as SKILL.md
shows, and read [acp.md](acp.md) before any action that can change the runtime.
