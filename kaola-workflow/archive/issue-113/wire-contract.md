# Issue #113 — the ZCode output-limit wire contract (mission 1)

Established read-only from `/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs`
(14,796,911 B, mtime 2026-09-20) and the live tree. Field names below are transcribed from the
app's own zod schemas, not inferred.

## The app's own predicate (authoritative)

    classifyOutputTokenContinuation(e) =
      e.toolCallCount > 0 || !isOutputTokenLimitFinishReason(e.finishReason, e.rawFinishReason)
        ? "none" : e.continuationCount < 3 ? "continue" : "exhausted"

    isOutputTokenLimitFinishReason(finishReason, rawFinishReason) =
      finishReason === "length"
      || new Set(["max_tokens","max_output_tokens","model_context_window_exceeded"])
           .has(rawFinishReason ?? "")

So the four tokens named in issue #113 are exactly right, and the auto-continue budget is 3.
`max_tokens` / `model_context_window_exceeded` / `max_output_tokens` are RAW PROVIDER finish
reasons; the provider mappers normalise them to the canonical `"length"`. On the continue path the
app also force-sets `K.finishReason = "length"`.

On exhaustion the app throws
`ModelError("The model's response exceeded the output token maximum.")` with
`context: {providerCode:"model_output_limit_exceeded", reason:"model_output_limit_exceeded",
source:"provider"}` and `recoverable: true`.

## What actually reaches the adapter

The app-server `session/event` type union (`cBi` / `lHt`) contains **no `turn.terminal`** — only
`turn.started`, `turn.steerQueued`, `turn.steerDrained`, `turn.completed`, `turn.failed`, the
message/part/model/tool/permission/userInput events, `checkpoint.created`, `rewind.triggered`,
`streamRecovery.updated`. The adapter's existing `turn.terminal` branch serves the other
(`kind:`-tagged) family and stays defensive.

`turn.completed` payload (`fir`, **strict**):
`response, tokenCount, usage?, toolCallCount, historyRoundCount?, duration, cacheStats?, inputId?,
resultType, backgroundSubagentResultConsumed?` where
`resultType ∈ {success, cancelled, error_max_turns, error_max_budget, error_during_execution,
error_max_tool_calls}`.
**It carries no finish reason at all**, and none of its `error_max_*` values is an output-token
limit — they are turn/budget/tool-call caps. Translating on `resultType` would be a false positive.

`turn.failed` payload (`mir`, **strict**): `error, turnPhase, inputId?,
backgroundSubagentResultConsumed?`.
`error` (`cHt`, **strict**): `type, message, stack?, code?, detail?, underlyingErrorMessage?,
underlyingErrorDetail?, attribution?, retryable?, data?` (`data` is `unknown`, so nested payloads
ride there).
`attribution` (`Bj`, **strict**): `source?, reason?, errorPhase?, exceptionKind?, providerId?,
modelId?, providerKind?, transport?, statusCode?, providerErrorCode?, retryable?`.

Note the rename: the error *context*'s `providerCode` is surfaced in attribution as
**`providerErrorCode`**, and the context's `reason` as `attribution.reason`. Both carry
`model_output_limit_exceeded`. `type` is `fr.ModelError = "model_error"`.

**Conclusion: the real output-token-max terminal arrives as `turn.failed`**, which today collapses
to ACP `refusal` at `scripts/kaola-zcode-acp.py:1531`.

## Design fixed for mission 3

Translate to `stopReason: "max_tokens"` on either signal, checked over the terminal payload:

1. an output-limit identity token `model_output_limit_exceeded` appearing as the error's
   `attribution.providerErrorCode` / `attribution.reason` / `code` / `type` (and inside `data`,
   which the throw site nests);
2. a finish-reason-bearing field equal to `length` or to one of the three raw tokens.

Deliberately NOT keyed on the broad `model_context_exceeded` error type: that class also covers
`prompt_too_long` / `context_length_exceeded`, i.e. INPUT context overflow, which is not an
output-token-max stop. Keying on the named tokens keeps the translation precise.

`cancelled` keeps precedence over `max_tokens` everywhere, preserving the existing cancel
semantics. Holder outcome mapping is unaffected: `turn_canceled` iff stop == `cancelled`, so both
the old `refusal` and the new `max_tokens` continue to yield `turn_completed`.

## Holder facts

`scripts/kaola-acp-holder.py:1693-1694` stores `stopReason` verbatim with no whitelist, and
`:1710` / `:1790` / `:1826` / `:3198` / `:3293` propagate it into `record.json`
`last_prompt.stop_reason`, `status` and the turn receipt. But `events.jsonl` has **no** event kind
carrying a turn's stop reason today (the kinds are session_update, notification, process_exited,
worker_event*, heartbeat_carrier*, permission*, steer*, config_options_applied, …), so the
`events.jsonl` half of issue #113 item 2 is a genuine addition, not a no-op.
