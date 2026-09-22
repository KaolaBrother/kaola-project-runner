# Bricked Host

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
   bricked `sess_*`; no in-Skill resume until one is proven live.
3. Continue the frontier from existing project records -
   `.kaola/heartbeat-prompt.json`, mission ledgers, Runner receipts - never
   re-claim, re-dispatch, or redo.
