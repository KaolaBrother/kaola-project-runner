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

## Quota-exhausted Host

Act only on confirmed exhaustion of the Host's own quota: an explicit
runtime/provider error or usage fact in its capture, receipts or events. A
generic 429, authentication error, timeout, transient failure, or
reset-window metadata alone is not: report it and keep the Host. No probe or
retry loop; existing records keep the evidence and any known pool/reset facts.

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
3. The exhausted Host is already ZCode, or the ZCode Host cannot start or
   operate: preserve the recovery state and ask the user. Never recreate the
   same exhausted Host, switch automatically to another platform, loop, or run
   two Hosts.

Never log in: do not attempt, retry or delegate login, logout/login cycling,
credential refresh or replacement, or account switching, and change no
credentials, billing routes or purchased quota. Authentication evidence is
reported for the user to handle. A seat the Host revoked for exhaustion stays
out of later handoffs and KPR-update reconciliation until the user
reauthorizes it. Worker-seat exhaustion is the Host's (Project Runner
`references/quota-packages.md`).
