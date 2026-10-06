# Substantive task failure

Decide the next owner when a worker substantively fails an engineering task. This is the dispatch and acceptance policy. It adds no schema, scheduler, or second heartbeat. Preset, count, Class, task, effort, tool, role, grant, and same-seat rules stay in [worker-profiles.md](worker-profiles.md). Confirmed quota or rate-limit failure, and authentication or account failure, stay in [quota-packages.md](quota-packages.md).

## Trigger

Judge the concrete evidence. Act when the core objective is unreachable, the evidence disproves the approach, or the same acceptance obligation receives a second Host `repair` verdict for the same responsible owner.

One failed attempt is one Host `repair` verdict on one formal submission of that obligation. A submission is a delivery claimed complete, a full gate or package result returned for acceptance, or an outside review the Host records as `repair`. The tool keeps the current owner's rejection count at that verdict. Absent is unknown, never zero. The second count, on a different submission, is the escalation trigger.

These are not attempts: a worker's own red test, a work-in-progress consult, a pre-declared scoped experiment, and a stall. One verdict counts once, whatever the number of findings or the exit code. A green self-test does not erase a `repair`. A later different defect on the same obligation still counts. A package, candidate, task-name, or session-shell rename does not reset the count. Editing `acceptance` does not clear it. A new prompt or strategy, with the same owner and effort, is not escalation.

The first `repair` stays with that owner. No timer and no failure classifier run inside the worker's own loop. Fix a demonstrated tool or environment cause and verify it on that seat; record the evidence before the next attempt. A cause that was never shown, and comes back as `repair`, counts. A connection wait is not by itself a model-capability failure ([qa-evidence.md](qa-evidence.md)).

## Escalation

Escalation means a different authorized owner now diagnoses or executes the obligation, or a higher effort where the Elite branch below allows it. The voucher is the dispatch or the effort receipt. `next` says what that owner does differently. Research may accompany the change. It does not replace a change of owner or effort ([public-research.md](public-research.md)).

An effort raise resets a segment only when the platform catalog declares an explicit semantic strength order for both tokens and the really-applied token is strictly later. No current platform catalog declares one, so the automatic effort-raise reset is effectively unavailable today; this is a documented limitation, not a claim of cross-platform automatic effort-upgrade recognition. A responsibility handoff with index evidence still resets.

When no suitable authorized seat or effort exists, record a local hold with `resume_when` and leave the count. Say that escalation is not done. The same seat may run only a pre-declared scoped experiment until the hold lifts. Substantive new scope is a new obligation. The old unresolved responsibility stays with its count.

The Host records the verdict and chooses the handoff. The Delegator supervises: it may tell the Host that escalation is owed, and it does not dispatch or name a seat. The Sideagent transcribes Host verdicts and does not judge them. The tool keeps the count. It does not choose the next owner and it does not block a dispatch.

## Next owner

Use only seats current authorization already allows. A task may move to a different already-authorized seat and runtime through existing lifecycle operations. Only a bound seat cannot be hot-switched or have its runtime changed in place. A same-seat model or preset change stays the safe-idle lifecycle in [worker-profiles.md](worker-profiles.md). An effort-only adjustment does not by itself grant or require a model switch. Owner restrictions stand.

**Worker failure.** Prefer an available, already-authorized Elite whose profile fits the failure, under the role limits in [worker-profiles.md](worker-profiles.md). If none is available or authorized, choose another eligible Worker for the actual need (investigation, reasoning, or implementation) and a materially different next approach.

**Elite failure.** When insufficient reasoning is the plausible gap, first raise effort on the same model when the runtime supports a higher effort, existing authorization permits it, and the owner's current restriction allows that raise. Role limits stay in [worker-profiles.md](worker-profiles.md). If effort cannot be raised because it is already at its supported ceiling, the runtime cannot raise it, the owner's current restriction forbids the raise, or effort is irrelevant to the failure, reassignment to another fitting already-authorized Elite remains a recovery before any request for new authorization: prefer one better suited to the problem, or, when none is clearly better suited, a complementary Elite with a concrete different approach. There is no universal effort ladder and no fixed model ranking.

**Knowledge gap.** When a failure may turn on missing external evidence — an upstream defect, a version limit, an unknown method or environment fact — consider whether that calls for research ([public-research.md](public-research.md)) rather than another same-approach elevation. Missing knowledge and insufficient reasoning can coexist, so research can complement an elevation or reassignment; neither must come first.

**No useful recovery.** When no eligible already-authorized recovery remains, report the specific gap and seek the missing authorization or task decision through the existing authorization route or `HUMAN_DECISION_REQUIRED`. Do not rotate indefinitely through models, and do not retry the same approach without new information.

## Handoff

Write in accordance with ASD-STE100.

Keep the original issue and run, the valid work, and the evidence. One writer owns the work. Checkpoint and hand off through existing lifecycle operations, and exact-stop the previous seat once it no longer owns the task. In the existing run records and the current heartbeat frontier, record only the substantive failure evidence, the attempted approach, the preserved output locator, and what the next owner will do differently. Those four facts are current frontier state. Do not rewrite an immutable `failed` or `done` mission line, and do not create a second ledger ([issue-dispatch.md](issue-dispatch.md)). You keep QA and acceptance: recheck the affected evidence and the actual gap. An extra full suite or an independent reviewer is not required.
