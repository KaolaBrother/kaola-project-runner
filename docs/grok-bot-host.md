# Grok Bot host

Grok Bot is a Project Runner **host**, at the same rank as Codex, Claude Code,
Cursor, and Devin. It is not an eighth CLI worker.

| Id | Meaning | Installer flag |
|---|---|---|
| `grok-bot` | Grok Bot desktop/cloud host (one Private Skill payload) | `--runtime grok-bot` |
| `grok` | Grok CLI worker (ACP `grok agent stdio`) | `--platform grok` |

`--platform grok-bot` is invalid. `--runtime grok` is not a host alias.

## Delivery shape: one Private Skill, seven embedded workers

Grok Bot discovers **one** Skill. `./scripts/render-skills.py --write` emits
`hosts/grok-bot/kaola-project-runner/`:

```text
hosts/grok-bot/
  .generated-by-kaola-project-runner
  kaola-project-runner/            # the only discoverable SKILL.md
    SKILL.md                       # Project Runner root: policy + worker routing
    references/                    # grok-bot-host.md, heartbeat-skeleton.md
    workers/<platform id>/         # seven embedded workers (supporting resources)
      WORKER.md                    # the worker contract (its SKILL.md, renamed)
      references/  scripts/        # platform facts, adapters, Runner scripts
```

The seven platforms stay seven platforms: each worker keeps its own manifest,
adapter, and scripts, byte-identical to `skills/<id>-kaola-project-runner/`
except that `SKILL.md` becomes `WORKER.md` and Skill identity files are
dropped. No worker is a separately discoverable Skill, and the root never
depends on a sibling Skill directory. `--check` and
`scripts/kaola-grok-bot-verify.py` prove exactly one root skill, seven
embedded workers, no plugin manifest, no sibling dependency, and no unofficial
Sand API identifiers.

## Payload integrity: the shared generation source is the truth

`hosts/grok-bot/` is generated output and is never hand-edited. Two checks
enforce that, and both re-render from the shared templates instead of trusting
the bytes on disk:

- `./scripts/render-skills.py --check` compares the whole `hosts/grok-bot/`
  tree against a fresh render and fails on any missing, unexpected, or stale
  file.
- `./scripts/kaola-grok-bot-verify.py hosts/grok-bot --repo .` re-renders the
  payload from `templates/`, `platforms/`, and `scripts/` and requires every
  file in the payload (root `SKILL.md`, `agents/openai.yaml`, `references/`,
  and every embedded worker resource) to be byte-identical, with no extra
  files, no symlinks, and executable bits only on `.sh` scripts. Without
  `--repo` the verifier proves shape only, not generated state.

`scripts/kaola-grok-bot-package.py` always runs the `--repo` form before
zipping and refuses to package a payload that drifts from the generated state,
so a hand-edited root `SKILL.md` or a stray file at the payload root can never
be signed into the archive.

## Individual plans (Ultra): private-skill hand-off, not a claimed upload path

Individual plans have no Team Marketplace. The official Grok Bot docs
(skills-routines-and-automations, settings-and-notifications; read 2026-09-15)
describe **Settings → Plugins → Yours** only as the surface to review and
enable plugins and **private skills** that already exist on the account. They
describe private skills as saved from a Bot conversation or taught as a task,
and packaged skills as installed from the Marketplace. They document no
control to upload or import a local directory or archive there, and nothing
about a private skill carrying a file tree with scripts. This project
therefore claims no official ingestion entry point.

The payload and its archive are a hand-off artefact for the owner's manual
UAT: the owner attempts to establish it as a private skill on the Bot and
records the exact outcome or gap (see Live UAT). Build it with

```bash
./scripts/render-skills.py --write
./scripts/kaola-grok-bot-package.py            # build/grok-bot/kaola-project-runner-grok-bot-skill.zip + .sha256
```

The archive is deterministic (same payload bytes, same digest) and contains
only `kaola-project-runner/…`. Team Marketplace / admin-provided plugins are an
optional path only on Teams or Enterprise plans. **Never publish this payload
to a public Marketplace.**

## Local execution copy

The Bot's Agent Computer is a cloud machine; the desktop app is a client. When
the CLI sessions live on this Mac, keep an identical copy of the same Skill on
this machine and use **Execution on Local Computer**:

```bash
./scripts/install-local.sh --runtime grok-bot
# payload: ${KAOLA_GROK_BOT_HOME:-$HOME/.kaola/grok-bot}/skills/kaola-project-runner
```

That copy is only the execution surface for a worker's `SKILL_DIR`
(`…/workers/<platform id>`) and `scripts/runtime-tmux.sh`; Grok Bot does not
discover anything on this disk. `--platform` and `--no-orchestrator` are refused
for this runtime (the payload is delivered whole), no other installed Skill
directory is read or written, and bin links stay off. Default copy;
`--method link` links the generated payload.

## Control plane on Grok Bot

The root Skill owns policy. On this host:

- One Routine on **this Bot conversation** is the only heartbeat. Do not stack
  it with a Codex heartbeat or sleep.
- Takeover cancels only the previous host heartbeat. Do not stop in-flight
  exact owned worker sessions.
- `HUMAN_DECISION_REQUIRED` stays in this Bot (Needs attention / Notifications).
  Agent Computer takeover is not CLI stop.
- Exact-session stop is still the matching worker's Runner `stop`, now called
  through the embedded `workers/<id>/scripts/runtime-tmux.sh`.
- Mission-frontier done is review, not automatic finalize.

See `skills/kaola-project-runner/references/grok-bot-host.md`.

## Live UAT (human; not claimed by this change)

1. Attempt to establish the payload as a private skill on the Bot. Settings →
   Plugins → Yours is the documented review/enable surface; no upload or
   import control is documented there. Record the exact outcome or gap,
   including whether Project Runner appears under Yours and can be enabled.
2. `/` in that Bot offers Project Runner; no separate worker Skill is needed.
3. A Routine fires in the same Bot conversation.
4. Local Computer runs `…/workers/<id>/scripts/runtime-tmux.sh` / `kaola-acp`
   against existing Mac sessions.
5. Takeover from a Codex heartbeat leaves busy workers running.
6. Worker `HUMAN_DECISION_REQUIRED` surfaces as Needs attention; takeover UI is
   not used as stop.
7. Frontier done does not self-finalize.

## Rollback

```bash
./scripts/install-local.sh --runtime grok-bot --uninstall   # removes only the owned payload copy
```

If a private skill was established on the Bot, disable or delete it under
Settings → Plugins → Yours. Pause or delete the Routine; restore the previous
host wake if needed. Do not Reset Agent Computer. Do not stop unrelated
workers.

## Out of scope

Unofficial Sand gateways, GrokBot RPCs, NCI, `platforms/grok-bot.yaml`, public
Marketplace publication, and Grok CLI as a host (`--runtime grok`).
