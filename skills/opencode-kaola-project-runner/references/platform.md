# OpenCode adapter

- Platform ID: `opencode`
- Default binary: `opencode`
- Binary override: `OPENCODE_BIN`
- Standalone session prefix: `opencode-kaola-<purpose>` (under Project Runner the name is issue-scoped; see SKILL.md)
- Resume: `session/resume`/`session/load` per advertised capability; Continue: the latest `session/list` entry for the canonical cwd
- Runner default preset (`--tier default`): **CLI native opening model** — `no Runner model or effort override`
- Runner upgrade preset (`--tier upgrade`): equals default here
- Fast support: no native Fast toggle; speed-named catalog models such as zhipuai-coding-plan/glm-5.3-flash are explicit model choices, not a Fast switch

## Preflight

Verify the OpenCode executable and report optional Kaola carrier/configuration evidence without gating communication, plus loopback=direct|excluded|ensured: what the opencode child sees once a forward proxy is set (ensured means the Runner appends the missing loopback entries).

Preflight is read-only: optional Kaola/Workflow surfaces and runtime health are reported as
evidence, and their absence does not block starting the CLI. It never installs, upgrades, adopts,
or rewrites runtime configuration. A requested model absent from or unknown to the readable
catalog is still launched as the exact declared literal, and the catalog fact is reported.

## Launch

ACP runs opencode acp. ACP has no skip-all, so ACP start sets no mode and permit settles each request; configOptions.mode is agent identity (build/plan), not skip-all.

The Agent decides every action; operate through `"$SKILL_DIR/scripts/runtime-tmux.sh"` as SKILL.md
shows, and read [acp.md](acp.md) before any action that can change the runtime.
