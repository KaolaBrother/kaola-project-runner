# Grok Bot host

Grok Bot is a host for this Skill, at the same rank as Codex, Claude Code,
Cursor, and Devin. It is not a worker and not an eighth CLI platform.
`--platform grok` installs the Grok CLI worker Skill. `--platform grok-bot` is
invalid. `--runtime grok` is not a host alias.

## Delivery shape: one Private Skill

Grok Bot discovers **one** Skill: this root `SKILL.md`. The seven platform
workers are embedded under `workers/<platform id>/` as supporting resources
(contract file `WORKER.md`, plus that worker's `references/` and `scripts/`).
No sibling Skill has to be discovered or enabled, and no worker is a separate
Skill in this payload.

Individual plans (for example Ultra) have no Team Marketplace. The documented
entry point is **Settings → Plugins → Yours**: add the payload as a private
skill and enable it for the Bot. Team Marketplace / admin-provided plugins are
an optional path only on Teams or Enterprise plans. Never publish this payload
to a public Marketplace.

Live enablement in the Grok Bot UI is a human UAT step. A payload on disk or
an archive is not live adoption.

## Local execution copy

The Bot's cloud computer is a different machine from this Mac. When the CLI
sessions live here, keep an identical copy of this Skill on this machine
(`./scripts/install-local.sh --runtime grok-bot`, default
`$HOME/.kaola/grok-bot/skills/kaola-project-runner`) and use **Execution on
Local Computer**. A worker's `SKILL_DIR` is that copy's `workers/<platform
id>`; its Runner entry is `SKILL_DIR/scripts/runtime-tmux.sh`. Do not treat
`/workspace` on the cloud computer as the Mac tmux/ACP holders.

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
