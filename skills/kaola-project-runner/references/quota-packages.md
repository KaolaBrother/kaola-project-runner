# Quota packages

Read this when receipts, captures, or events show an explicit limit or an account refusal. Package shape and display rules live in checkout `docs/api.md`. The pool is the refusal text or a receipt's `quotaPool`; an unmapped pool proves neither way. This file does not change granted counts and has no account-repair procedure.

## Confirmed exhaustion

**Trigger.** An explicit exhaustion, a reached rate limit, or a stated reset/window/account limit. A bare 429, timeout, network error, reset metadata without a limiting reason, or a connecting/awaiting seat is unknown: keep it, report a persistent blocker, and do not probe or retry.

**Expert.** Preserve the task, output, and native resume id, and ask the user. No substitute Expert, no reuse of an old grant, no downgrade. Unrelated work continues.

**Elite.** Preserve the output and locator, and safely reclaim (exact-stop) the seat. Revoke this run-seat: remove its availability from this run's heartbeat snapshot. Hand the task to another suitable, already-authorized Elite that is not on the known limited pool, within granted/shared counts and current resource limits. Never restart it under the old grant or switch its model to get around the limit; only the user reauthorizes.

**Worker.** Another suitable Worker takes the task under the pool permission. Pool permission and real limits apply. Never cycle seats of a known limited shared pool.

**No eligible same-class replacement.** Report with evidence and ask. Never cross classes, create grants, or discard work.

**Continuity.** The replacement continues the same run (worktree, ledger, receipts) with one writer, no duplicate claim, and no redo. Revocation touches only this seat in this run. Owner-confirmed availability replaces stale exhaustion; a revoked Elite grant stays revoked. Neither an availability refresh nor a passed reset restores it; only the user's explicit reauthorization does.

**Authentication or account refusal** (including an explicit refusal with no class remedy) is not this branch: [Account unavailable](#account-unavailable). The Host's own failure is the Delegator's `kaola-delegator` `references/host-brick.md`.

Never log in: no attempt, retry, delegation, cycling, credential refresh or replacement, account switching, or billing/quota change. No account diagnosis, quota restoration, or retry loop.

## Account unavailable

An explicit `login expired`, `authentication required`, revoked or invalid credentials, `account disabled`, or an equivalent account-access refusal takes this branch, including an explicit refusal with no class remedy. A timeout, 429, network error, or uncertain message does not: keep the unknown and report a blocking access failure if the seat cannot continue. The class branches above never apply, and there is no automatic substitution.

Pause the seat; this is not a revocation. Preserve the task, locator, output, and identity, give it no new work, exact-stop it once the turn settles, and mark it paused. Report the runtime, the exact message, and what was preserved. Ask for no secrets. No other seat takes that task before the user directs. Resume only on the user's direction, from existing records, with no duplicate claim. Never log in.
