# Bricked, limit-failed or account-unavailable Host

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

**Limit, same trigger** as Project Runner `references/quota-packages.md`: a confirmed limit failure of the Host's own account. Unknown evidence, an authentication or account refusal, or a brick does not use this fallback; a brick keeps its same-platform replacement above. Preserve the frontier from records (grants including revoked seats, issues, evidence, worker ownership, pending close-out).

- **Non-ZCode Host.** Exact-stop it, prove it gone, and start one ZCode Host as a new ACP session under the carried authorization. Do not re-ask the platform. Never `--resume` another runtime's native id as ZCode. Re-claim and redo nothing.
- **Host already ZCode, or ZCode cannot start or operate.** Preserve and ask the user.
- **Never.** Recreate the same limited Host, switch automatically elsewhere, loop, or run two Hosts.

Never log in. Seats the Host revoked stay out of later handoffs and KPR-update reconciliation until the user reauthorizes them. Worker-seat limit failure stays the Host's (`references/quota-packages.md`).

## Account-unavailable Host

An explicit `login expired`, `authentication required`, revoked or invalid credentials, `account disabled`, or an equivalent account-access refusal. A timeout, 429, network error, or uncertain message stays unknown: no login, and report a blocking access failure if the Host cannot continue. This never uses the ZCode fallback.

Pause the Host and preserve the frontier, including each in-flight worker's session, native resume id, worktree, and valid output. Bind no new work, exact-stop it once it settles, and mark it paused. Report the runtime, the exact message, and what was preserved. Ask for no secrets. Resume the same Host only on the user's direction. No automatic substitution and no login.
