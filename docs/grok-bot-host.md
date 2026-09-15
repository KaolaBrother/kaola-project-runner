# Grok Bot host

Grok Bot is a Project Runner **host**, at the same rank as Codex, Claude Code,
Cursor, and Devin. It is not an eighth CLI worker.

| Id | Meaning | Installer flag |
|---|---|---|
| `grok-bot` | Grok Bot desktop/cloud host (eight single-Markdown Private Skills + one Local Computer runtime copy) | `--runtime grok-bot` |
| `grok` | Grok CLI worker (ACP `grok agent stdio`) | `--platform grok` |

`--platform grok-bot` is invalid. `--runtime grok` is not a host alias.

## Delivery shape: eight single-Markdown Private Skills, one runtime copy

Owner UAT on candidate `91b2e26` (2026-09-16) established the account-side fact
that shapes this delivery: a Grok Bot private skill is **one single Markdown**
saved through the Bot's skill write (observed as `update_state`) with only
`name`, `description`, and `body`. There is no ZIP import and no multi-file
tree import; Settings → Plugins → Yours has no import tool. So the account
receives **eight Skills**, and the file tree stays on this Mac.
`./scripts/render-skills.py --write` emits `hosts/grok-bot/`:

```text
hosts/grok-bot/
  .generated-by-kaola-project-runner
  INSTALL.md                       # repo-based guide Grok Bot itself follows (not a Skill)
  private-skills.json              # fingerprint manifest: name, description, body/file sha256
  private-skills/                  # exactly eight account-private Skill documents
    kaola-project-runner.md        # main Skill (Project Runner)
    claude-code-kaola-project-runner.md
    codex-kaola-project-runner.md
    cursor-cli-kaola-project-runner.md
    devin-kaola-project-runner.md
    grok-kaola-project-runner.md
    kimi-cli-kaola-project-runner.md
    opencode-kaola-project-runner.md
  kaola-project-runner/            # Local Computer runtime copy (scripts live here)
    SKILL.md                       # orchestrator root with embedded-worker routing
    references/                    # grok-bot-host.md, heartbeat-skeleton.md
    workers/<platform id>/         # seven embedded workers (supporting resources)
      WORKER.md                    # the worker contract (its SKILL.md, renamed)
      references/  scripts/        # platform facts, adapters, Runner scripts
```

Each account document is rendered from the shared templates and manifests,
never hand-written:

- `kaola-project-runner.md` is `templates/orchestrator/SKILL.md.tmpl` rendered with a
  routing table that names the seven worker Skills by their **stable Skill
  names**. It owns authorization recovery, heartbeat, dispatch,
  acceptance-before-finalize, and close-out. It carries no transport contract,
  no scripts, and none of the worker text, and its two references are bundled
  verbatim at its end.
- `<id>-kaola-project-runner.md` is that worker's canonical
  `skills/<id>-kaola-project-runner/SKILL.md` **verbatim** (the full transport
  contract: preflight, start, observe, send, capture, key, stop), followed by
  its Local Computer script location and its three references
  (`platform.md`, `transport.md`, `acp.md`) bundled verbatim. It carries no
  orchestrator policy.

Every document has a unique frontmatter `name` equal to its file stem, a
`description`, and a body; it reaches nothing outside itself (no `../`, no
sibling Skill directory, no file-tree link), so each one can be saved on its
own. Seven platforms stay seven platforms: there is no
`platforms/grok-bot.yaml`, and no worker Skill is named after Grok Bot.

## Grok Bot installs the eight Skills itself

The owner does not copy any body by hand. Grok Bot reads this checkout on
Local Computer and follows `hosts/grok-bot/INSTALL.md`:

1. Verify the checkout and candidate: `git rev-parse HEAD` equals the commit the
   owner named; `python3 scripts/render-skills.py --check` and
   `python3 scripts/kaola-grok-bot-verify.py hosts/grok-bot --repo .` pass.
2. Read the eight files in the guide's order; for each, take `name` and
   `description` from the frontmatter and the body after the closing `---`, and
   save it with the Bot's own skill write. Eight calls, one per source file. An
   existing Skill with the same name is updated in place; no duplicate is ever
   created and no name is changed. Re-running is idempotent and touches no
   other Skill on the account.
3. Keep a checklist (`created` / `updated` / `FAILED (reason)` / `not
   attempted`); retry only failed rows; report partial completion as partial.
4. Verify the eight identities under Settings → Plugins → Yours and in `/`,
   then let Project Runner select a worker by its stable Skill name and run the
   Local Computer script.

The guide uses only the Bot's own skill write and Local Computer file reads: no
shell or API bypass, no unofficial Sand API, no account credential, no ZIP
import, and never a public Marketplace. It is a hand-off for the owner's manual
UAT, not a claimed official ingestion entry point.

## One canonical Skill system; Grok Bot is a packaging adapter

The eight documents are produced by the `grok-bot` host adapter inside `render-skills.py` (the
delimited "Host adapter: grok-bot" section). Its inputs are only the canonical sources —
`templates/orchestrator/`, `templates/SKILL.md.tmpl`, `templates/agents/`,
`templates/references/`, `platforms/*.yaml`, `scripts/` — plus `templates/grok-bot/`, which
holds only the install-guide prose. Its outputs are the eight standalone Markdown documents, the
`private-skills.json` fingerprint manifest (name, description, `body_sha256`, `file_sha256` per
document), the runtime copy, and `INSTALL.md`. Host differences live only in that adapter layer
(reference expansion, Local Computer path hints, the single-Markdown form, the Bot's install
steps); scheduling, safety, and transport semantics come from the canonical sources and change
only there. No `platforms/grok-bot.yaml`, no `scripts/adapters/grok-bot.sh`, no second
hand-written body. See [architecture](architecture.md#host-adapters-one-canonical-skill-system).

## Payload integrity: the shared generation source is the truth

`hosts/grok-bot/` is generated output and is never hand-edited. Two checks
enforce that, and both re-render from the shared templates instead of trusting
the bytes on disk:

- `./scripts/render-skills.py --check` compares the whole `hosts/grok-bot/`
  tree (the eight documents, the guide, and the runtime copy) against a fresh
  render and fails on any missing, unexpected, or stale file.
- `./scripts/kaola-grok-bot-verify.py hosts/grok-bot --repo .` proves the shape
  (exactly eight documents, 1 main + 7 workers, unique names, main routes to all
  seven names and absorbs no transport, workers absorb no orchestrator policy
  and state their Local Computer location, every document standalone, the
  guide lists exactly the eight sources, the runtime copy has one root
  `SKILL.md` and seven embedded workers, no plugin manifest, no symlinks,
  executable bits only on `.sh`) and, with `--repo`, byte identity of every
  file with the fresh render. Without `--repo` the verifier proves shape only.

`scripts/kaola-grok-bot-package.py` runs the `--repo` form before zipping the
runtime copy and refuses any drift; the archive moves the runtime copy between
machines and is not an account import.

## Individual plans (Ultra): private-skill hand-off, not a claimed upload path

Individual plans have no Team Marketplace. The official Grok Bot docs
(skills-routines-and-automations, settings-and-notifications; read 2026-09-15)
describe **Settings → Plugins → Yours** only as the surface to review and
enable plugins and **private skills** that already exist on the account. They
describe private skills as saved from a Bot conversation or taught as a task,
and packaged skills as installed from the Marketplace. They document no
control to upload or import a local directory or archive there. This project
therefore claims no official ingestion entry point; the Bot's single-Markdown
skill write is the owner-observed path, exercised by the Bot itself in UAT.

```bash
./scripts/render-skills.py --write             # hosts/grok-bot/private-skills/*.md, INSTALL.md, runtime copy
./scripts/kaola-grok-bot-verify.py hosts/grok-bot --repo .
```

Team Marketplace / admin-provided plugins are an optional path only on Teams or
Enterprise plans. **Never publish these Skills to a public Marketplace.**

## Local execution copy

The Bot's Agent Computer is a cloud machine; the desktop app is a client. When
the CLI sessions live on this Mac, keep the generated runtime copy on this
machine and use **Execution on Local Computer**:

```bash
./scripts/install-local.sh --runtime grok-bot
# runtime copy: ${KAOLA_GROK_BOT_HOME:-$HOME/.kaola/grok-bot}/skills/kaola-project-runner
```

Each worker Skill names its own `SKILL_DIR`
(`${KAOLA_GROK_BOT_HOME:-$HOME/.kaola/grok-bot}/skills/kaola-project-runner/workers/<id>`)
and Runner entry (`$SKILL_DIR/scripts/runtime-tmux.sh`); `KAOLA_GROK_BOT_HOME`
overrides the root. The installer copies only the runtime copy: the eight
account documents and the guide are not installed here, Grok Bot does not
discover anything on this disk, `--platform` and `--no-orchestrator` are refused
for this runtime, no other installed Skill directory is read or written, and
bin links stay off. Default copy; `--method link` links the generated tree.

## Control plane on Grok Bot

The main Skill owns policy. On this host:

- One Routine on **this Bot conversation** is the only heartbeat. Do not stack
  it with a Codex heartbeat or sleep.
- Takeover cancels only the previous host heartbeat. Do not stop in-flight
  exact owned worker sessions.
- `HUMAN_DECISION_REQUIRED` stays in this Bot (Needs attention / Notifications).
  Agent Computer takeover is not CLI stop.
- Exact-session stop is still the matching worker's Runner `stop`, reached by
  loading that worker's Private Skill and running its Local Computer script.
- Mission-frontier done is review, not automatic finalize.

See `skills/kaola-project-runner/references/grok-bot-host.md`.

## Live UAT (human; not claimed by this change)

1. Grok Bot follows `hosts/grok-bot/INSTALL.md` on Local Computer against the
   named candidate and saves the eight Skills one by one with its skill write.
   Record the checklist (eight rows), any failure, and any retry.
2. Settings → Plugins → Yours lists exactly the eight names, enabled, with no
   duplicate; `/` in that Bot offers all eight. Record the exact outcome or gap.
3. Project Runner selects one authorized worker by its stable Skill name, loads
   that worker Skill, and runs
   `~/.kaola/grok-bot/skills/kaola-project-runner/workers/<id>/scripts/runtime-tmux.sh`
   on Local Computer against an existing Mac session.
4. A Routine fires in the same Bot conversation.
5. Takeover from a Codex heartbeat leaves busy workers running.
6. Worker `HUMAN_DECISION_REQUIRED` surfaces as Needs attention; takeover UI is
   not used as stop.
7. Frontier done does not self-finalize.

## Rollback

```bash
./scripts/install-local.sh --runtime grok-bot --uninstall   # removes only the owned runtime copy
```

Disable or delete the eight Skills under Settings → Plugins → Yours. Pause or
delete the Routine; restore the previous host wake if needed. Do not Reset
Agent Computer. Do not stop unrelated workers.

## Out of scope

Unofficial Sand gateways, GrokBot RPCs, NCI, `platforms/grok-bot.yaml`, public
Marketplace publication, ZIP or file-tree import claims, and Grok CLI as a host
(`--runtime grok`).
