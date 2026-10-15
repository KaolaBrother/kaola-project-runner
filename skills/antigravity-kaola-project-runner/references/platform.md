# Antigravity adapter

- Platform ID: `antigravity`
- Default binary: `agy`
- Binary override: `AGY_BIN`
- Standalone session prefix: `antigravity-kaola-<purpose>` (under Project Runner the name is issue-scoped; see SKILL.md)
- Resume: `session/resume`/`session/load` per advertised capability; Continue: `unsupported`
- Runner default preset `antigravity/default` (`--tier default`): **Gemini 4 Argon** — `gemini-4-argon-medium` with `effort=medium (encoded in model ID)`
- Runner xhigh preset `antigravity/xhigh` (`--tier xhigh`): **Gemini 4 Argon** — `gemini-4-argon-high` with `effort=high (encoded in model ID)`
- Runner opus preset `antigravity/opus` (`--tier opus`): **Claude Opus 5.5** — `claude-opus-5-5-high` with `effort=high (encoded in model ID)`
- Fast support: no native Fast toggle; the catalog's low, medium and high slugs are explicit model choices, not a Fast switch

## Preflight

Verify the agy executable and report `agy --version`; never run a model turn and never write under ~/.gemini. Sign-in is not a preflight fact: the probe session/new reports login_required from agy's own start-up refusal.

Preflight is read-only: optional Kaola/Workflow surfaces and runtime health are reported as
evidence, and their absence does not block starting the CLI. It never installs, upgrades, adopts,
or rewrites runtime configuration. A requested model absent from or unknown to the readable
catalog is still launched as the exact declared literal, and the catalog fact is reported.

## Launch

The local ACP adapter runs the exact AGY_BIN as one long-lived `agy --input-format stream-json --output-format stream-json --print-timeout 0s` child per session, with --model and --dangerously-skip-permissions applied from the ACP model and mode options. Effort is baked into the model id (gemini-4-argon-{low,medium,high}); the adapter never passes --effort, so effort cannot be applied twice. A sign-in or account-eligibility refusal is reported as login-required with the browser verify URL.

Native launch policy, when this adapter supports it, is reported separately from ACP mode
selection. Read the platform permission facts in [acp.md](acp.md); existing explicit policy
and contrary modes take precedence over a managed default.

The Agent decides every action; operate through `"$SKILL_DIR/scripts/runtime-tmux.sh"` as SKILL.md
shows, and read [acp.md](acp.md) before any action that can change the runtime.
