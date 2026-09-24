# Cursor CLI adapter

- Platform ID: `cursor-cli`
- Default binary: `cursor-agent`
- Binary override: `CURSOR_AGENT_BIN`
- Standalone session prefix: `cursor-cli-kaola-<purpose>` (under Project Runner the name is issue-scoped; see SKILL.md)
- Resume: `session/resume`/`session/load` per advertised capability; Continue: the latest `session/list` entry for the canonical cwd
- Runner default preset (`--tier default`): **Grok 4.7 Extra High** — `grok-4.7-xhigh` with `effort=xhigh (encoded in model ID), fast=false`
- Runner upgrade preset (`--tier upgrade`): **Claude Opus 5.5 High** — `claude-opus-5-5-high` with `effort=high (encoded in model ID)`
- Fast support: Fast via the ACP parameterized `fast` option (true/false strings), which applies to any model; a `-fast` catalog id (e.g. grok-4.7-xhigh-fast) decomposes onto that option; an unsupported variant is reported rather than invented

## Preflight

Verify the Cursor executable and report optional global/project Workflow command evidence without gating communication.

Preflight is read-only: optional Kaola/Workflow surfaces and runtime health are reported as
evidence, and their absence does not block starting the CLI. It never installs, upgrades, adopts,
or rewrites runtime configuration. A requested model absent from or unknown to the readable
catalog is still launched as the exact declared literal, and the catalog fact is reported.

## Launch

ACP runs cursor-agent --yolo acp, initialized with _meta.parameterizedModelPicker=true; configOptions.mode has no skip-all value, so ACP start sets no mode.

The Agent decides every action; operate through `"$SKILL_DIR/scripts/runtime-tmux.sh"` as SKILL.md
shows, and read [acp.md](acp.md) before any action that can change the runtime.
