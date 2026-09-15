# Grok Bot host

Grok Bot is a host for this Skill, at the same rank as Codex, Claude Code,
Cursor, and Devin. It is not a worker and not an eighth CLI platform.
`--platform grok` installs the Grok CLI worker Skill. `--platform grok-bot` is
invalid. `--runtime grok` is not a host alias.

## Delivery shape: eight account-private Skills plus one runtime copy

On a Grok Bot account a private skill is one single Markdown: `name`,
`description`, `body`. Owner UAT (2026-09-16) found no way to import a ZIP or
a multi-file tree. So the account receives **eight** Skills, each its own
document rendered from the shared templates under
`hosts/grok-bot/private-skills/`: `kaola-project-runner` (this Skill: authorization
recovery, heartbeat, dispatch, acceptance-before-finalize, close-out) and one
`<platform id>-kaola-project-runner` per worker (its full transport contract
and its Local Computer script location). This Skill routes to a worker by that
stable Skill name; it never inlines worker text and never loads a file tree.
No Skill on the account depends on a sibling file or on another Skill being
saved. Grok Bot installs and updates all eight itself from the repository by
following `hosts/grok-bot/INSTALL.md` (one skill write per file, idempotent by
name). Still seven platforms; no worker is an eighth platform.

Individual plans (for example Ultra) have no Team Marketplace. The official
Grok Bot docs describe **Settings → Plugins → Yours** only as the surface to
review and enable plugins and private skills that already exist on the
account; they document no control to upload or import a local directory or
archive there. The eight documents are a private-skill hand-off for manual
UAT, not a claimed official ingestion entry point. Team Marketplace /
admin-provided plugins are an optional path only on Teams or Enterprise plans.
Never publish these Skills to a public Marketplace.

Live enablement in the Grok Bot UI is a human UAT step. A document or a
runtime copy on disk is not live adoption; record the exact outcome or gap.

## Local execution copy

The Bot's cloud computer is a different machine from this Mac. When the CLI
sessions live here, keep the generated runtime copy on this machine
(`./scripts/install-local.sh --runtime grok-bot`, default
`$HOME/.kaola/grok-bot/skills/kaola-project-runner`, root overridable with
`KAOLA_GROK_BOT_HOME`) and use **Execution on Local Computer**. That copy is
one directory with the seven workers' scripts and references embedded under
`workers/<platform id>/`; each worker Skill states its own `SKILL_DIR`
(`<copy>/workers/<platform id>`) and Runner entry
(`SKILL_DIR/scripts/runtime-tmux.sh`). Do not treat `/workspace` on the cloud
computer as the Mac tmux/ACP holders.

## Heartbeat

On Grok Bot, one Routine bound to **this Bot conversation** is the only
heartbeat carrier. Do not stack it with a Codex heartbeat, a Grok CLI `/loop`,
or same-session blocking sleep. After close-out, pause or delete that Routine
rather than leaving it firing.

Record the Routine identity in the consuming project's run records, not in this
Skill.

## Takeover and rollback

When Grok Bot takes over from another host, cancel only that host's recurring
wake. Do not stop in-flight exact owned worker sessions. Do not Reset Agent
Computer. Do not use the Bot "Stop now" control as Runner `stop`.

Idle exact-session stop remains the matching platform Runner `stop`, ACP
and PTY alike.

Restoring the previous host means pausing or deleting this Routine and
re-creating that host's single wake. Workers may keep running across the switch.

## Decisions

`HUMAN_DECISION_REQUIRED` is considered here first and, when it must reach the
human, stays in **this Bot conversation** (Needs attention / this Bot's
Notifications). Agent Computer takeover is for passwords, passkeys, 2FA,
CAPTCHAs, and similar blocked site steps. It is not a CLI decision channel and
not exact-session stop.

## Authorization and acceptance

Recover existing explicit authorization and live work before asking intake
questions. A completed mission frontier still requires review and acceptance
before finalize. A Routine success, idle worker, or green CI is not acceptance.

Do not call unofficial Sand gateways or GrokBot RPCs. Official Skill, private
skill, Routine, Local Computer, and notification surfaces are the host contract.
