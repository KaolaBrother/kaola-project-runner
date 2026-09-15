# Grok Bot host

Grok Bot is a first-class host for this Skill, at the same rank as Codex, Claude
Code, Cursor, and Devin. It is not a worker and not an eighth CLI platform.
`--runtime grok-bot` installs the generated Cursor-plugin bundle. `--platform grok`
installs the Grok CLI worker Skill. `--platform grok-bot` is invalid.

Live enablement in the Grok Bot 0.51.x UI is a human UAT step. An installer copy
or plugin payload on disk is not live adoption.

## Load

Workers are sibling Skills under this plugin's `skills/` directory. Resolve each
worker Skill directory and call its `scripts/runtime-tmux.sh` the same way as on
any other host. Prefer **Execution on Local Computer** when the seven CLI
sessions live on this machine. The Grok Bot cloud computer is a different
machine; do not treat `/workspace` on that computer as the Mac tmux/ACP holders.

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

Idle exact-session stop remains the matching platform Runner Skill `stop`, ACP
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

Do not call unofficial Sand gateways or GrokBot RPCs. Official Skill, Plugin,
Routine, Local Computer, and notification surfaces are the host contract.
