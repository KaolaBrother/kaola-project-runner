# Retrieval notes — durable-returns branch

Access date for all: 2026-10-04. Fetcher: Devin webfetch/web_search (read-only HTTPS). Quotes kept
short; paraphrase otherwise. Docs pages are "current docs" (no per-page version stamp captured);
source files carry the blob commit where GitHub reported one.

## Temporal official docs (docs.temporal.io, current)

- https://docs.temporal.io/tasks — fetched full. "Any event that might affect the Workflow's state
  triggers a new Workflow Task. The Workflow Task bundles together all new events that have occurred
  since the last Workflow Task completed." Worker "replays the entire Workflow Execution from the
  beginning using the Event History"; previously executed ops return results from history; crash →
  "another Worker can pick up the Workflow Task and replay the entire history." Separate section:
  "Workflow Task failure... automatically retried... Execution stays Open" vs Workflow Execution
  failure (business logic, closes Failed). Activity API provides an "'effectively once' experience"
  even though several Activity Task Executions may run. Heartbeat payload carried across retries.
  Nexus: operation handler "should be idempotent"; WorkflowRunOperation "leverages Workflow ID
  bas[ed dedup]" (tail truncated in fetch but consistent).
- https://docs.temporal.io/handling-messages — fetched full. Messages processed "in the order they
  were received" on a single-threaded loop; handlers run before main method in some cases; await
  "All Handlers Finished" before run completes or Continues-As-New; Handler Unfinished Policy
  Abandon → "clients waiting for Updates will get Not Found errors". Dedup: Updates deduped on
  server by Update ID (auto UUID, can set your own); "For Signals, you should use a custom
  idempotency key that you send as part of your own signal inputs"; both Signals and Updates
  "automatically use request IDs to deduplicate retried client calls"; per-run scope — carry own
  dedup across Continue-As-New. Update Validator: accept → "part of your Workflow's history" +
  client notified Accepted; reject → "Workflow will have no indication that it was ever requested".
  Signal handler non-Application exceptions → Workflow Task failure → retried until fixed
  ("Workflow will get stuck").
- https://docs.temporal.io/sending-messages — fetched full. startUpdate wait stages: Accepted
  ("wait until the Worker is contacted, which ensures that the Update is persisted") or Completed.
  Signal-With-Start: atomic ("if running, Signaled; otherwise starts and is immediately sent the
  Signal"). Update-With-Start: requires WorkflowIDConflictPolicy; "Unlike Signal-with-Start —
  Update-With-Start is not atomic. If the Update can't be delivered... a new Workflow Execution
  will still start. The SDKs will retry... no guarantee that the Update will succeed." Attach rule:
  same Update ID on existing workflow attaches to existing Update; on closed workflow attaches only
  if Update completed. Update feature flags needed pre-v1.25.0; Update-With-Start recommends
  server v1.28.
- https://docs.temporal.io/encyclopedia/workflow-message-passing — fetched full. Queries read /
  Signals async write (no awaited result) / Updates "synchronous, tracked write requests". Table:
  use Signals when "Clients don't depend on the Worker being available"; Updates when "You want to
  validate the Update before accepting it into the Workflow and its history" and need result/error.
- https://docs.temporal.io/activity-execution — fetched full. "Temporal guarantees that an Activity
  Task either runs or timeouts"; task loss not detected directly — Start-To-Close timeout → retried
  per Retry Policy. Async Activity Completion: function returns without completing; external system
  completes via Task Token OR (Namespace)+Workflow ID+Activity ID. Caveat: "a Task Token is unique
  for an Activity execution, retries can cause a remote service using the Task Token to end up with
  an invalid one" — doc recommends Activity ID + Workflow ID instead. Guidance: async completion if
  external system unreliable / needs heartbeat+cancellation; else Signal gives faster retry because
  a short-timeout notify Activity retries quickly while a week-long Start-To-Close delays retry.
- https://docs.temporal.io/workflow-execution/workflowid-runid — fetched full. At most one Open
  execution per Workflow ID in a Namespace. Conflict Policy: Fail (default, "Workflow execution
  already started" error), Use Existing (returns running Run Id), Terminate Existing. Reuse Policy
  governs Closed IDs (Allow Duplicate default / Failed Only / Reject / Terminate-If-Running).
  Retention period bounds closed-ID checks (default ~30 days). Run ID is platform-level, mutable
  across Retry/ContinueAsNew/Reset — "shouldn't rely on the current Run Id".
- https://docs.temporal.io/encyclopedia/detecting-workflow-failures — via search snippet.
  Workflow Task Timeout default 10s: "primarily available to recognize whether a Worker has gone
  down so that the Workflow Execution can be recovered on a different Worker."
- https://docs.temporal.io/troubleshooting/request-failures — via search snippet. NOT_FOUND on
  task result: task timed out / execution closed / worker restarted mid-execution; "the Temporal
  Service threw away the result your Worker just produced"; WorkflowTaskTimedOut event + reschedule
  (sticky cache evicted, cold replay on retry).
- https://docs.temporal.io/troubleshooting/execution-failures — via search snippet. Non-determinism
  → WorkflowTaskFailed event, service retries the task forever until compatible code arrives.
- https://docs.temporal.io/design-patterns/request-response-via-updates — via search snippet.
  "Within a single Workflow Execution, the Server deduplicates retried Updates automatically by
  Update ID"; only track IDs across Continue-As-New. "Exceeding the 2,000 total Updates limit...
  `SuggestContinueAsNew` at 90%." "Set a stable, business-meaningful updateId when you want a
  retried Update-with-Start to attach to an existing in-flight Update instead of starting duplicate
  work."
- https://docs.temporal.io/design-patterns/signal-with-start — via search snippet + fetch attempt.
  Atomic; entity-workflow examples implement `processed_items` dedup set inside workflow code.
- https://docs.temporal.io/guides/entity-pattern-loyalty-points — via search snippet. "Temporal
  delivers Signals at least once. Include a deduplication key in Signal payloads and make your
  Signal processing logic idempotent." Carries `processed_event_ids` (bounded window ~last 1,000 +
  external store for long-term) and `pending_events` (signals arrived but unprocessed) across
  Continue-As-New explicitly.
- https://typescript.temporal.io/api/enums/proto.temporal.api.enums.v1.UpdateWorkflowExecutionLifecycleStage —
  via search snippet. ADMITTED = "admitted by the server... does not wait for any sort of
  acknowledgement from a worker"; ACCEPTED = "passed validation on a worker"; COMPLETED =
  "executed to completion on a worker". If requested stage not reached before server timeout,
  "server returns actual stage reached" (honest partial-stage readback).

## Temporal source (github.com/temporalio/*)

- https://github.com/temporalio/temporal/blob/main/service/history/api/signalworkflow/api.go —
  fetched at main HEAD 2026-10-04 (commit pin not captured). `Invoke`: if `request.GetRequestId()
  != "" && mutableState.IsSignalRequested(request.GetRequestId())` → Noop action (dedupe). Then
  `mutableState.AddSignalRequested(requestId)`; `AddWorkflowExecutionSignaledEvent(...)`; workflow
  task created unless first-WFT backoff. Closed workflow → `consts.ErrWorkflowCompleted`. Also
  returns a `Link` (request-id ref link to the signaled event) in the response.
- https://github.com/temporalio/temporal/blob/53e04440/service/history/workflow/update/registry.go —
  search snippet at commit 53e04440 (same content at b4fbfe00). `FindOrCreate(updateID)` returns
  `alreadyExisted`; `Find` checks in-memory admitted/accepted map then `store.GetUpdateOutcome`
  (completed updates persisted — dedup survives restart). `checkTotalLimit` FailedPrecondition:
  "Make sure any duplicate updates share an Update ID so the server can deduplicate them".
- https://github.com/temporalio/temporal/blob/53e04440/service/history/workflow/update/update.go —
  search snippets (also seen at b4fbfe00). `Admit`: "if the state is anything other than
  stateCreated then it just early returns a nil error. This effectively gives us Update request
  deduplication by updateID." Request payload kept in registry until written to history in an
  UpdateAccepted event; UpdateAdmitted/UpdateAccepted are real history events. WaitStage code:
  completed-outcome first, then accepted-future; returns actual reached stage on timeout.
- https://github.com/temporalio/temporal/blob/b4fbfe00/service/history/api/updateworkflow/api.go —
  search snippet at b4fbfe00. `firstExecutionRunId` mismatch → `ErrWorkflowExecutionNotFound`
  (exact chain correlation). Not running → `Find(updateID)`: existing update → `Noop: true`
  ("repeated Update requests with the same ID see the same result"), else `ErrWorkflowCompleted`.
  Paused workflow → FailedPrecondition. `WorkflowTaskAttempt >= failUpdateWorkflowTaskAttemptCount`
  → `serviceerror.NewWorkflowNotReady` — fail the update fast when the workflow task is stuck.
- https://github.com/temporalio/api/blob/b4bdd8035cd1883aa96cbad5bb0e582850feea5f/temporal/api/workflowservice/v1/request_response.proto —
  search snippet at that commit. `StartWorkflowExecutionRequest.request_id` = "A unique identifier
  for this start request. Typically UUIDv4." `RequestCancelWorkflowExecutionRequest.request_id` =
  "Used to de-dupe". TypeScript SDK ref for SignalWorkflowExecutionRequest: `requestId` — "Used to
  de-dupe sent signals."
- https://github.com/temporalio/api/blob/main/temporal/api/workflowservice/v1/service.proto —
  search snippet. `SignalWorkflowExecution`: "This results in a WORKFLOW_EXECUTION_SIGNALED event
  recorded in the history and a workflow task being created."

## Community lead (not proof)

- https://community.temporal.io/t/preliminary-investigation-into-idempotent-signals/13694 —
  forum investigation confirming request_id dedups signals, request id "isn't stored in the
  Workflow Execution Signaled Event, but is stored in the workflow's mutable state", dedup code in
  signalworkflow/api.go. Matches the source I read directly; cited as corroboration only.

## Comparable systems / pattern literature

- https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html — fetched full.
  `.waitForTaskToken`: task pauses; token obtained from Context object `$$.Task.Token`; external
  system returns token + payload via `SendTaskSuccess` / `SendTaskFailure`; `SendTaskHeartbeat`
  extends liveness; default wait up to the 1-year service quota; `HeartbeatSeconds` recommended so
  a missing callback fails with `States.Timeout`. Same-account principal restriction on tokens.
- https://microservices.io/patterns/data/transactional-outbox.html — fetched full (pattern
  literature, design claim not measured result). Store message in DB in the same transaction as
  the business update; relay publishes at-least-once; "a message consumer must be idempotent,
  perhaps by tracking the IDs of the messages that it has already processed." Relay may publish
  twice if it crashes between publish and recording that fact.

## Not verified / knowledge gaps

- Exact pending-signal queue limits and self-hosted dynamic-config defaults (only update limits
  were confirmed: 2,000/run total per docs; in-flight concurrency limited).
- Whether `IsSignalRequested` dedup IDs survive workflow Reset/migration across versions (mutable
  state implies within-run persistence; not checked further).
- Delivery claims are documented behavior + code reading, not measured tests; no benchmarks run.
