# Substantive task failure

Decide the next owner when a worker substantively fails an engineering task. This is the dispatch and acceptance policy. It adds no schema, scheduler, or second heartbeat. Preset, count, Class, task, effort, tool, role, grant, and same-seat rules stay in [worker-profiles.md](worker-profiles.md). Confirmed quota or rate-limit failure, and authentication or account failure, stay in [quota-packages.md](quota-packages.md).

## Trigger

Judge the concrete evidence. Act when the core objective is unreachable, the evidence disproves the approach, or repeated repair no longer makes meaningful progress on the core problem. Routine errors, small fixes, and productive debugging stay with the current worker, including a rejected delivery whose repair is still that assignment. There is no fixed retry count, timer, or failure classifier. A connection wait, or an environment or tool failure, is addressed as the demonstrated cause; it is not by itself a model-capability failure ([qa-evidence.md](qa-evidence.md)).

## Next owner

Use only seats current authorization already allows. A task may move to a different already-authorized seat and runtime through existing lifecycle operations. Only a bound seat cannot be hot-switched or have its runtime changed in place. A same-seat model or preset change stays the safe-idle lifecycle in [worker-profiles.md](worker-profiles.md). An effort-only adjustment does not by itself grant or require a model switch. Owner restrictions stand.

**Worker failure.** Prefer an available, already-authorized Elite whose profile fits the failure, under the role limits in [worker-profiles.md](worker-profiles.md). If none is available or authorized, choose another eligible Worker for the actual need (investigation, reasoning, or implementation) and a materially different next approach.

**Elite failure.** When insufficient reasoning is the plausible gap, first raise effort on the same model when the runtime supports a higher effort, existing authorization permits it, and the owner's current restriction allows that raise. Role limits stay in [worker-profiles.md](worker-profiles.md). If effort cannot be raised because it is already at its supported ceiling, the runtime cannot raise it, the owner's current restriction forbids the raise, or effort is irrelevant to the failure, reassignment to another fitting already-authorized Elite remains a recovery before any request for new authorization: prefer one better suited to the problem, or, when none is clearly better suited, a complementary Elite with a concrete different approach. There is no universal effort ladder and no fixed model ranking.

**No useful recovery.** When no eligible already-authorized recovery remains, report the specific gap and seek the missing authorization or task decision through the existing authorization route or `HUMAN_DECISION_REQUIRED`. Do not rotate indefinitely through models, and do not retry the same approach without new information.

## Handoff

Keep the original issue and run, the valid work, and the evidence. One writer owns the work. Checkpoint and hand off through existing lifecycle operations, and exact-stop the previous seat once it no longer owns the task. In the existing run records and the current heartbeat frontier, record only the substantive failure evidence, the attempted approach, the preserved output locator, and what the next owner will do differently. Those four facts are current frontier state. Do not rewrite an immutable `failed` or `done` mission line, and do not create a second ledger ([issue-dispatch.md](issue-dispatch.md)). You keep QA and acceptance: recheck the affected evidence and the actual gap. An extra full suite or an independent reviewer is not required.
