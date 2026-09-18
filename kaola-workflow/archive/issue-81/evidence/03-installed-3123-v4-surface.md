# Issue #81 — Mission 3: installed ZCode 3.12.3 v4 surface (read-only bundle inspection)

Date: 2026-09-19. Source: `/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs`
(11,416,833 bytes, mtime 2026-09-16; desktop build 3.12.3.7463, CLI reports 0.16.5).
Read-only string/schema extraction; no process started, no credential file opened.
Minified identifiers (`iu`, `dWi`, `eJt`…) are bundle-local names, quoted so the
experiment can recognize the same code paths at runtime.

## 1. v4 is served on the SAME `app-server --stdio` dispatch as `session/*`

One `dispatchRequest(t)` switch handles both families (offset ~11275881):

```js
case iu.command: return this.requireV4Gateway().handleCommand(t.params);
case iu.commandsQuery: return this.requireV4Gateway().queryCommands(t.params);
case dr.sessionCreate: return await T8n(this.context,t.params,t.trace);
case dr.sessionResume: return await A8n(this.context,t.params);
```

`requireV4Gateway()` lazily provides the v4 gateway in-process — **no separate
channel, port, or subcommand is needed**. The v4 method-name map (`iu`):

```js
{connectionFlow:"v4/connection/flow",
 controllerSubscribe:"v4/controller/subscribe", controllerResync:"v4/controller/resync",
 controllerUnsubscribe:"v4/controller/unsubscribe",
 conversationSubscribe:"v4/conversation/subscribe", conversationResync:"v4/conversation/resync",
 conversationUnsubscribe:"v4/conversation/unsubscribe",
 conversationRowsRange:"v4/conversation/rowsRange", conversationPlans:"v4/conversation/plans",
 conversationFileChanges:"v4/conversation/fileChanges",
 conversationFileRewindPreview:"v4/conversation/fileRewindPreview",
 usageStats:"v4/usage/stats", conversationUsage:"v4/conversation/usage",
 attachmentBegin/Chunk/Commit/Abort/Read/PreviewSource:"v4/attachment/*",
 conversationAttachmentRead:"v4/conversation/attachmentRead",
 conversationAttachmentStat:"v4/conversation/attachmentStat",
 commandsQuery:"v4/commands/query", command:"v4/command"}
```

Notifications to the client (`YB`): `conversationFrame:"v4/conversation/frame"`,
`conversationTelemetryFact:"v4/telemetry/event"`,
`cuaPermissionObservation:"v4/cua/permission-observation"`.

## 2. `v4/command` — envelope, admission, CAS

Envelope (`dWi`, `parseCommandEnvelope`):

```js
{commandId:string, clientId:string, sessionId:string|null,
 baseRevision?:number, baseLogEpoch?:string, type:uWi, payload:unknown, issuedAt}
```

Command types (`uWi = keys(G0n)`): `createSession`, `createSelectionSideSession`,
`sendText`, `sendGoalCommand`, `compact`, `stop`, `resolveInteraction`,
`forkAssistant`, `applyFileRewind`, `editUserQuery`, `retryTurn`,
`setAssistantFeedback`, `sendQueuedNow`, `editQueueItem`, `reorderQueueItem`,
`deleteQueueItem`, `setAutoDrain`, `switchModelConfig`,
`switchCollaborationMode`, `setFollowupMode`, `pauseGoal`, `resumeGoal`,
`deleteSession`, `discardSharedContext`.

**CAS rules** (`CommandInbox.decide`, ~10809885):

- unknown/null `sessionId` (except `createSession`) → ack
  `{commandId, status:"rejected", reasonCode:"proto.sessionNotFound", revisionAtDecision}`
- `i4t` commands (queue/state mutations incl. `setFollowupMode`,
  `sendQueuedNow`, `setAutoDrain`, `switchModelConfig`, `pauseGoal`…) REQUIRE
  `baseRevision` → else `{status:"rejected", reasonCode:"proto.missingBaseRevision"}`
- `s4t` commands (`applyFileRewind`,`forkAssistant`,`editUserQuery`,`retryTurn`,
  `setAssistantFeedback`) ALSO require `baseLogEpoch == current` → else
  `{status:"stale", reasonCode:"proto.staleLogEpoch"}`
- malformed → `{status:"rejected", reasonCode:"proto.invalidPayload"}`
- statuses observed: `accepted | rejected | stale | failed` (+`result` on success,
  `message` sometimes); `v4/commands/query` re-fetches a command's final ack.

`sendText` payload schema:

```js
sendText: {text:string, attachments?:[], requestedDelivery?:"startNow"|"queue"|"guide",
  browserAmbientContext?, context_refs?:[]max1,
  heldQueueDisposition?:"clearQueueAndSend"|"keepQueueAndSend",
  expectedHeldQueueItemIds?:string[], modelSelection?:{providerId,modelId,options?},
  mode?:enum, planEnabled?:boolean, modelExecution?, automationId?, offPeakTaskId?,
  offPeakRunType?:"init"|"resume", botDeliveryTarget?, toolDisallowlist?:string[]}
```

`setFollowupMode` payload: `{mode:"queue"|"guide"}` — needs `baseRevision`.

## 3. sendText admission semantics (handler `zIs`, ~10997958)

- `requestedDelivery` default = session `inputRouting.mode` (`guide`→guide,
  `enqueue`→queue, else `startNow`); the per-command field wins.
- `startNow`: acquires a foreground promotion lease
  (`send-now:<commandId>`; busy → throws `fault.command.inputRejected`
  "send now foreground promotion is busy"), then `preemptActiveTurnAndWait`
  (abortMessage `"v4 sendText startNow preempts active turn"`) — **startNow
  preempts the running turn, like legacy `session/send`** (the v3 handler
  literally wraps `sendText{requestedDelivery:"startNow"}` with
  `clientId:"legacy-session-send"`).
- `guide` + attachments → `fallbackReasonCode:"guide.attachmentsUnsupported"`
  and falls back.
- `inputRouting.mode==="choice"` requires `heldQueueDisposition` +
  `expectedHeldQueueItemIds` validation (`applyHeldQueueDisposition`).
- Result: `{type:"inputAccepted", delivery:"queue"|"startNow",
  inputId:<commandId>}` — merged into the ack as
  `{commandId,status:"accepted",revisionAtDecision,result:{…}}`.
  **The result alone does NOT distinguish guide-queued from plain-queued** —
  both report `delivery:"queue"`. The injected-vs-queued distinction lives in
  the events (§5).

## 4. Steer admission inside a turn (runtime, `B_n`/`q_n`, ~9605247)

- Turn objects carry `steerable:boolean`; submission validates
  `expectedTurnId` when given: mismatch → `rejectTurnSteer("expected_turn_mismatch")`;
  `!steerable` → `rejectTurnSteer("turn_not_steerable")`;
  empty/oversize → `rejectTurnSteer("empty_input"|"input_too_large")`.
- Persisted intent records (`tUe`):
  `delivery:{requested:"auto"|"startNow"|"queue"|"guide",
             admitted:"startNow"|"queue"|"guide", fallbackReasonCode?},
   order:{admissionSeq, queuePosition?},
   steer:{state:"notRequested"|"submitting"|"steering"|"guided"|"fellBack",
          reasonCode?},
   dispatch:{state:"admitted"|"queued"|"reserved"|"promoting"|"drained"},
   admittedAt`.
- `stateRevision` increments per session state mutation
  (setModel/setFollowupMode/setAutoDrain…); `session.updated` events carry
  `{eventSeq, stateRevision, activeTurnId?, pendingRequestIds, …}` — the value
  to echo as `baseRevision` in CAS commands.

## 5. The distinguishing events (shared event enum `iXn` = `zcodeSessionEventTypeSchema`)

`iXn` enumerates `session.created|resumed|updated|titleUpdated|closed`,
`turn.started`, **`turn.steerQueued`**, **`turn.steerDrained`**,
`turn.completed`, `turn.failed`, `message.upserted|removed`,
`part.started|delta|upserted|removed`, `model.streaming`, `tool.updated`,
`permission.*`, … This enum validates `session/event` payloads — the SAME enum
the v3 `session/subscribe` channel emits — and the v4 frame event registry
(`jc("turn.steerQueued",eJt)` etc.).

`turn.steerQueued` payload (`eJt`, strict):

```js
{pendingInputId, inputId?, queryId?, input:string, inputPreview, inputSize:int,
 commandKind?:"sendText"|"sendGoalCommand"|"compact", source?:"plan_approval_feedback",
 toolDisallowlist?:[], delivery?:"queue"|"guide", targetTurnId, queueLength:int, intent?}
```

`turn.steerDrained` payload (`tJt`, strict):

```js
{pendingInputIds:[], queryIds?:[], targetTurnId, injectedMessageIds:[],
 drainedInputs?:[{pendingInputId, messageId, text, delivery?, intent?, toolDisallowlist?}]}
```

`turn.started` (`XKt`): `{turnNumber, input, inputId?, queryId?, inputSource?,
executionKind?:"agent"|"controlOnly", messageId?, …}`.
`turn.completed` (`rJt`): `{response, tokenCount, usage?, toolCallCount,
historyRoundCount?, duration, cacheStats?, inputId?, resultType:"success"|"cancell…"}`.
`turn.failed` (`nJt`): `{error, turnPhase, inputId?, …}`.

**Evidence-grade reading of the same turn:**
- `turn.steerQueued{delivery:"guide", targetTurnId:T}` then
  `turn.steerDrained{targetTurnId:T, injectedMessageIds:[…]}` while `T` is
  active ⇒ consumed mid-turn (injected).
- `turn.steerQueued{delivery:"queue"}` or a steer that survives `T`'s
  `turn.completed` without `steerDrained` ⇒ queued, NOT injected.
- `rejectTurnSteer` / `status:"rejected"` / `status:"stale"` ⇒ rejected.
- command ack `failed` / no ack / no events ⇒ unknown.

## 6. `v4/conversation/subscribe` and frames

Subscribe params (`GLe = FVi.extend`): `{topic:"conversation/<id>",
base?:{logEpoch,seq}, visibility?:"foreground"|"background", connectionId,
clientMode:"desktop-continuous"|"web-remote-replayable", workspace?,
legacyTaskIds?≤200, resumeThoughtLevel?}`.
Result `{ack:{subscriptionId, mode:"snapshot"|"resume", logEpoch, openTiming?}}`;
initial wires are delivered as `v4/conversation/frame` notifications AFTER the
response (postResponseOutbox). Resync: `{subscriptionId, base:{logEpoch,seq}|null,
forceSnapshot?, topic, connectionId}`.

`v4/connection/flow` params `{connectionId, state:"saturated"|"drained"|"closed"}`.

## 7. What stays unproven until live (for M4)

- Whether `session/event` (v3 subscribe) emits `turn.steerQueued`/`steerDrained`
  or only the v4 frame stream does — the enum is shared, delivery is the question.
- Whether a v3 `session/create` session id is directly usable as the v4
  `sessionId` in commands (the session registry lookup `ta(e,t.sessionId)`
  suggests yes).
- Whether a regular agent turn is `steerable` on this build, and what
  `guide` does when the turn is not steerable (`fellBack` vs reject vs queue).
- The exact `v4/conversation/frame` envelope fields (topic/seq/logEpoch/event).
