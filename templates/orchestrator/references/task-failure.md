# Substantive task failure

Decide the next owner when a worker substantively fails an engineering task. This is the dispatch and acceptance policy. It adds no engine, registry, schema, scheduler, benchmark, or second heartbeat. Preset, count, Class, task, effort, tool, and same-seat rules stay in [worker-profiles.md](worker-profiles.md). Confirmed quota or rate-limit failure, and authentication or account failure, stay in [quota-packages.md](quota-packages.md).

## Trigger

Judge the concrete evidence. Act when the core objective is unreachable, the evidence disproves the approach, or repeated repair no longer makes meaningful progress on the core problem. Routine errors, small fixes, and productive debugging stay with the current worker, including a rejected delivery whose repair is still that assignment. There is no fixed retry count, timer, or failure classifier. A connection wait, or an environment or tool failure, is addressed as the demonstrated cause; it is not by itself a model-capability failure ([qa-evidence.md](qa-evidence.md)).

## Next owner

Use only seats current authorization already allows. Grant no model or seat. Reassignment moves the task to another authorized seat through existing lifecycle operations. It does not hot-switch a bound seat or change runtime. A same-seat model, preset, or effort change stays the idle same-seat rule in worker-profiles.md.

The branches below are Worker and Elite. Expert keeps its per-task permission and cannot implement. Do not assign it implementation, and do not treat a listed profile as permission.

**Worker failure.** Prefer an available, already-authorized Elite whose profile fits the failure, including that preset's role limits. If none is available or authorized, choose another eligible Worker for the actual need (investigation, reasoning, or implementation) and a materially different next approach. Do not invent an Elite grant.

**Elite failure.** When insufficient reasoning is the plausible gap, first raise effort on the same model if the runtime supports a higher effort and existing authorization permits it. An owner's fixed effort or other restriction stands. Raising effort changes only effort: `claude-code/opus-xhigh` stays thinking-only and does not implement. If effort is already at its supported ceiling, the runtime cannot raise it, or effort is irrelevant to the failure, choose another available, authorized Elite better suited to that problem. If none is clearly better suited, a complementary Elite is reasonable when it offers a concrete different approach. There is no universal effort ladder and no fixed model ranking.

**No useful recovery.** Report the specific gap and seek the missing authorization or task decision through the existing authorization route or `HUMAN_DECISION_REQUIRED`. Do not rotate indefinitely through models, and do not retry the same approach without new information.

## Handoff

Keep the original issue and run, the valid work, and the evidence. One writer owns the work. Checkpoint and hand off through existing lifecycle operations, and exact-stop the previous seat once it no longer owns the task. In the existing run records and the current heartbeat frontier, record only the substantive failure evidence, the attempted approach, the preserved output locator, and what the next owner will do differently. Those four facts are current frontier state. Do not rewrite an immutable `failed` or `done` mission line, and do not create a second ledger ([issue-dispatch.md](issue-dispatch.md)). You keep QA and acceptance: recheck the affected evidence and the actual gap. An extra full suite or an independent reviewer is not required.

## Cases

- **Worker to Elite.** A Worker cannot reach the core objective, and an already-authorized Elite profile fits that failure: that Elite continues from the preserved output. No new Elite grant.
- **Worker to Worker.** No fitting Elite is available or authorized: another eligible Worker takes the actual need with a materially different approach.
- **Elite effort.** Reasoning is the plausible gap, the runtime can raise effort, and authorization permits it, with no owner-fixed effort barring it: raise effort on that same model. The role stays the same.
- **Elite reassignment.** Effort is at its ceiling, unavailable, or irrelevant: another available authorized Elite better suited to the problem, or, when none is clearly better suited, a complementary Elite with a concrete different approach.
- **Unavailable authorization.** No eligible recovery remains: name the gap and ask. No model rotation, and no same-approach retry without new information.
- **Thinking-only.** Higher effort leaves `claude-code/opus-xhigh` thinking-only. Expert still requires explicit task permission and cannot implement. Neither receives an implementation task under this policy.
- **Preserved work.** The same issue and run continue under one writer. The frontier records the failure evidence, attempted approach, output locator, and the different next action. `failed` and `done` mission lines stay as written.
