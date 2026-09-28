# Bricked or quota-exhausted Host

A Host can brick: every shell call fails before the shell runs (for example
`spawn /bin/bash ENOENT` after its remembered working directory was moved or
removed). Runner `status` may still look healthy; the brick shows only in the
Host's reply. A bricked Host reports `brick`, asks to be replaced, and stops
acting.

Recovery belongs to the outer Agent:

1. Exact-stop that Host with `--expected-holder-instance-id` from its receipt
   and prove it gone, as in [handoff.md](handoff.md) Afterward.
2. Start a new standard-named `$HOST` at `$PROJECT`: a new ACP session under
   the current authorization (handoff Recover step 4). Do not `--resume` the
   bricked Host's native id; no in-Skill resume until one is proven live.
3. Continue the frontier from existing project records -
   `.kaola/heartbeat-prompt.json`, mission ledgers, Runner receipts - never
   re-claim, re-dispatch, or redo.

## Limit-failed Host

Act only on a confirmed limit failure of the Host's own account: an explicit
runtime/provider error or usage fact in its capture, receipts or events that
the quota is exhausted, a rate limit was reached, or a reset/window/account
limit was stated. A bare 429, timeout, network error, transient failure or
reset-window metadata without an explicit limiting reason is not, nor is a
session still connecting or awaiting a reply: keep the unknown and keep the
Host, observing at the existing cadence and escalating a persistent blocker
with evidence. No probe or retry loop; existing records keep the evidence and
any known pool/reset facts.

1. Preserve the frontier from those records: grants (Elite rows, approved
   Expert tasks, seats the Host revoked), issues and claims, valid evidence,
   worker ownership (sessions, native resume ids, worktrees) and pending
   close-out. The Host `stop` also ends its recorded inner holders.
2. A non-ZCode Host: this rule authorizes one ZCode Host; do not re-ask the
   Host platform. Exact-stop and prove gone as above, then start
   `zcode-<PROJECT_CODE>-orchestrator-<purpose>` as a new ACP session under
   the carried authorization, asking only missing or conflicting values.
   Never `--resume` another runtime's native id as ZCode. Hand off those
   facts in the existing fields; the new Host resumes attested worker seats,
   and nothing is re-claimed or redone.
3. The limited Host is already ZCode, or the ZCode Host cannot start or
   operate: preserve the recovery state and ask the user. Never recreate the
   same limited Host, switch automatically to another platform, loop, or run
   two Hosts.

Never log in: do not attempt, retry or delegate login, logout/login cycling,
credential refresh or replacement, or account switching, and change no
credentials, billing routes or purchased quota. A seat the Host revoked for a
limit failure stays out of later handoffs and KPR-update reconciliation until
the user reauthorizes it. Worker-seat limit failure is the Host's (Project
Runner `references/quota-packages.md`).

## Account-unavailable Host

An explicit `login expired`, `authentication required`, revoked/invalid
credentials, `account disabled` or equivalent account-access refusal in the
Host's capture, receipts or events establishes this path; a timeout, 429,
network error or uncertain message does not: keep the unknown, attempt no
login, and report a blocking access failure if the Host cannot continue. This
is not a limit failure: never invoke the ZCode fallback above or any other
Host replacement for it.

Pause the Host. Preserve the frontier and every in-flight worker's ownership
evidence (session, native resume id, worktree) and valid output, bind no new
work to it, then once its failed turn settles exact-stop it under the existing
safe lifecycle and mark it temporarily paused in the current run's
authorization/heartbeat snapshot. Contain it through that evidence and the
safe handoff boundary - force-clean no in-flight seat and drop no worker. The
pause is temporary: it neither revokes the user's grant nor deletes a
model/profile.

Report to the user the affected Host runtime, the exact runtime message, what
was preserved, and that account repair outside KPR or another course is the
user's call; ask for no secrets in chat, and never silently dispatch another
Host or seat for the blocked task before user direction.

After the user confirms restoration and directs continuation, resume that same
Host from the existing start/receipt records: no duplicate claim and no lost
valid work. A user-directed replacement Host follows that direction and the
existing seat/class boundaries. No automatic login probe or scheduled retry.
