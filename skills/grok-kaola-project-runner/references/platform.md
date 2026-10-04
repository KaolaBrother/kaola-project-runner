# Grok CLI adapter

- Platform ID: `grok`
- Default binary: `grok`
- Binary override: `GROK_BIN`
- Standalone session prefix: `grok-kaola-<purpose>` (under Project Runner the name is issue-scoped; see SKILL.md)
- Resume: `session/resume`/`session/load` per advertised capability; Continue: the latest `session/list` entry for the canonical cwd
- Runner default preset `grok/default` (`--tier default`): **Grok 4.7** — `grok-4.7` with `effort=xhigh, fast=false`
- Fast support: no native Fast mechanism; explicit --fast on is reported unsupported

## Preflight

Verify the Grok executable and report grok inspect catalog evidence without making Workflow availability a communication gate.

Preflight is read-only: optional Kaola/Workflow surfaces and runtime health are reported as
evidence, and their absence does not block starting the CLI. It never installs, upgrades, adopts,
or rewrites runtime configuration. A requested model absent from or unknown to the readable
catalog is still launched as the exact declared literal, and the catalog fact is reported.

## Launch

ACP runs grok agent --always-approve stdio; the agent advertises no mode option, so ACP start sets no mode.

Native launch policy, when this adapter supports it, is reported separately from ACP mode
selection. Read the platform permission facts in [acp.md](acp.md); existing explicit policy
and contrary modes take precedence over a managed default.

The Agent decides every action; operate through `"$SKILL_DIR/scripts/runtime-tmux.sh"` as SKILL.md
shows, and read [acp.md](acp.md) before any action that can change the runtime.
