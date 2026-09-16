# Grok Bot host (bridge host)

Grok Bot is a host for this Skill, at the same rank as Codex, Claude Code,
Cursor, and Devin. It is not a worker and not an eighth CLI platform.
`--platform grok` installs the Grok CLI worker Skill. `--platform grok-bot` is
invalid. `--runtime grok` is not a host alias, and there is no `--runtime
grok-bot`: nothing is installed for Grok Bot by the installer.

## Delivery shape: one thin account Skill, everything else in the repository

The account holds exactly one small private Skill, `kaola-project-runner`
(the bridge, generated into `hosts/grok-bot/`). It names the repository, the
accepted pinned revision, the device-local locator command, and the two entry
paths `ROOT/skills/kaola-project-runner` and
`ROOT/skills/<platform id>-kaola-project-runner`. It carries no policy,
transport, reference, worker text, path, or credential; a pin changes only its
accepted-revision line. Progressive disclosure holds on every host: this Skill
loads alone, one worker loads at dispatch, references load on demand, scripts
execute and are never read.

A delivery is two commits, because a commit cannot contain its own hash: the
**content commit R** (runtime, docs, tests; `accepted-revision.json` at stage
`content`, whose bridge says "none yet" and must not be saved) and the **pin
commit P** that follows it (stage `pinned`, commit R, an honest pre-release
label or a release tag at R). The bridge is saved from P; every execution target
is checked out clean and detached at R. `render-skills.py --check
--require-pinned` at P proves R exists, is an ancestor, is a content-stage
commit, holds the locator and every entry path, and that P differs from R only
by `accepted-revision.json` plus the three generated products with a one-line
bridge diff. Never rebase, squash, or amend an accepted R/P pair: if `main`
moves first, create a fresh R and P and repeat review and UAT. A release is a
tag at R followed by a new P naming it; rollback is a new P naming an older R.

## Execution targets: bind first, never cross

Grok Bot runs cloud Agent Computer projects and Local Computer (Mac) projects.
Nothing on one target is reachable from the other: not files, not the project,
not the CLI, not tmux, not sessions. The bridge binds the target first, then asks
that target's locator `kaola-project-runner-locate` (a re-registerable link to
`scripts/kaola-locate.py` in that target's own checkout) for ROOT, verifies
origin `github.com/KaolaBrother/kaola-project-runner`, HEAD = accepted revision,
and a clean tree, then accepts the consumer project root as a separate path on
the same target.

- Local Computer already holds the repository. Its `main` working tree may carry
  untracked Workflow records, which the locator correctly reports as `dirty`;
  the owner therefore selects a clean checkout or worktree detached at R (no
  fixed path is assumed and the clean check is never weakened). The cloud
  computer never clones, installs, updates, or manages anything on the Mac; the
  Mac path lives only in the Mac's locator link, never in the account Skill.
  Moving the checkout or changing R means re-registering the locator;
  `register --target local|cloud` validates origin, expected revision, and clean
  state before it touches an existing link, then atomically writes a
  credential-free registration receipt beside the link (resolved ROOT, declared
  target, host fingerprint, accepted revision) that stays device-local.
- The cloud target may keep its own independently cloned checkout and locator
  (its own existing Git or GitHub CLI authentication; never a token in any
  Skill, receipt, or prompt). That checkout never touches Mac paths or sessions.

## Attestation before dispatch (fail closed)

Run on the bound target before each worker dispatch:

```bash
kaola-project-runner-locate --target local|cloud --expect-revision <accepted> \
  --project <consumer project root> --worker <platform id> --session <exact session>
```

The receipt is one bounded JSON line: the target kind as you declared it, host
kernel and hashed hostname fingerprint, ROOT identity (normalised origin, HEAD,
clean, revision match), project identity (path on this host, Git top level,
normalised origin), the worker script path under the same ROOT, and whether tmux
reports a session of that exact name (presence only, on the tmux server the
locator can reach: not existence elsewhere, never ownership, which is the worker
preflight's proof). `--target` is the Agent's declaration: the script cannot
tell a Mac from a cloud computer. What ties the receipt to the bound target is
that the locator link is device-local and that the locator compares the running
`host.fingerprint` and the declared target with the value recorded at
registration in the receipt beside its link, refusing on mismatch, so a fresh
conversation needs no memory of it. `root.path` and `project.path` are real
local paths (they may include the user's home): bounded evidence for this target
that never enters any account Skill. `result: refused` with reasons
(`origin-mismatch`, `origin-form-unsupported`, `revision-mismatch`, `dirty`,
`locator-not-registered`, `host-fingerprint-mismatch`, `target-mismatch`,
`registration-stale`, `project-not-on-this-host`, `script-outside-root`,
`target-required`, `expect-revision-required`, ...) means do not load or dispatch; a path that does not
exist on the executing host is `project-not-on-this-host` whatever target was
declared. Revision and clean facts are what that host's Git reports; index
tricks or a tampered `.git` on a trusted host are outside this boundary. Then run
`ROOT/skills/<platform id>-kaola-project-runner/scripts/runtime-tmux.sh` on that
same target with the project root as `--repo`.

## Heartbeat

On Grok Bot, one Routine bound to **this Bot conversation** is the only
heartbeat carrier. Do not stack it with a Codex heartbeat, a Grok CLI `/loop`,
or same-session blocking sleep. After close-out, pause or delete that Routine
rather than leaving it firing. Record the Routine identity in the consuming
project's run records, not in this Skill.

## Takeover and rollback

When Grok Bot takes over from another host, cancel only that host's recurring
wake. Do not stop in-flight exact owned worker sessions. Do not Reset Agent
Computer. Do not use the Bot "Stop now" control as Runner `stop`. Idle
exact-session stop remains the matching platform Runner `stop`, ACP and PTY
alike. Restoring the previous host means pausing or deleting this Routine and
re-creating that host's single wake; workers may keep running across the switch.

## Decisions

`HUMAN_DECISION_REQUIRED` is considered here first and, when it must reach the
human, stays in **this Bot conversation** (Needs attention / this Bot's
Notifications). Agent Computer takeover is for passwords, passkeys, 2FA,
CAPTCHAs, and similar blocked site steps. It is not a CLI decision channel and
not exact-session stop.

## Authorization, acceptance, and the UAT boundary

Recover existing explicit authorization and live work before asking intake
questions. A completed mission frontier still requires review and acceptance
before finalize. A Routine success, idle worker, or green CI is not acceptance.

No supported automated way to create an account Skill exists
(`NO_SUPPORTED_PATH`), so the bridge arrives by one native skill write and a
saved bridge is not live adoption. The read-only Local Computer UAT (locate the
existing Mac checkout in a named workspace, register the locator, attest, run one
worker `preflight` against an existing project and session; nothing started,
sent, stopped, cloned, or installed) establishes placement on the bound target,
not live use. A real-use smoke on one session is separately authorized and is
never part of installation. Do not call unofficial Sand gateways or GrokBot
RPCs; never publish to a Marketplace.
