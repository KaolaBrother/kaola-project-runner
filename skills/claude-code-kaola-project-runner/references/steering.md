# Claude Code steering (`steer`)

Scope: the ACP channel only. Native steering on this platform's ACP surface:
**supported** (entry `_session/steering`). Native mid-turn steering on the ACP surface: the vendored bridge drives `claude --input-format stream-json` and a second user message written while the turn runs joins that turn (live probe, cli 2.1.272: one `result` event, num_turns 3, the steer replaced the remaining tool steps). The CLI acknowledges nothing for an injected message - the whole stdout stream carries no echo and no `user` event beyond tool results - so the bridge reports `written` with `steer_confirmation: write-only`, never `injected`. A steer written after the turn's `result` starts a NEW turn (probe: a second result event), so the bridge refuses once the turn settles and reports `unknown` for a write that races it.

`steer` has two modes and the Agent picks one. `--steer-mode native` uses the
native entry and exists only where the entry does. `--steer-mode interrupt` is
the composite that works on every platform. With no `--steer-mode`, a native
platform uses `native` and a platform without an entry **refuses**
(`steer-mode-required`) and writes nothing — the Runner never interrupts your
worker on its own, and never degrades from native to composite after a failure
or timeout.

`steer` delivers one Agent-chosen message to the turn **already running** on this exact session,
over the same routing as `send`: no scheduler, no second writer, no second lifecycle. The original
prompt keeps its request id, output, and terminal state, and the receipt's `turn_request_id`,
`turn_request_id_after`, and `turn_request_id_preserved` make that checkable. Content is literal
transport under the same identity, redaction, and bounded-receipt rules as `send`.

`steer_outcome` and `steer_consumed` are the only consumption claims:

| `steer_outcome` | `steer_consumed` | Meaning |
|---|---|---|
| `injected` | `true` | the agent acknowledged that the running turn took the text; adoption by the model is a separate question |
| `written` | `null` | the text was flushed into the running turn's input, but this platform acknowledges no consumption — read the turn's own output to judge |
| `interrupted_and_resent` | `true` | composite: the running turn was cancelled and confirmed stopped, then this text ran as the next turn |
| `resent_without_interrupt` | `true` | composite: the turn had already ended, so nothing was interrupted and this text ran as the next turn |
| `started_new_turn` | `true` | the agent opened a separate turn instead — not injection, and this holder does not track it |
| `not_consumed` | `false` | nothing was written (no active turn, or the turn had already settled); `send` a normal prompt if you still want it |
| `unsupported` | `false` | no native entry on this platform; nothing was written |
| `rejected` | `false` | the agent refused the request; `error.detail` carries its reason |
| `unknown` | `null` | no reply or an unrecognized outcome — consumption is undecided; do not resend blindly |

`steer_confirmation` says what backs the claim: `agent-confirmed` (the agent acknowledged it),
`write-only` (the bytes were flushed into the running turn and nothing more is knowable),
`cancel-confirmed` (the composite saw the old turn stop), or `none`. An `injected` claim without
`agent-confirmed` is a bug, not an optimism.

An idle session is never natively steered: the Runner refuses before writing, since some agents
answer an idle steering call by starting a detached turn. A turn that ends in the same instant is
decided by what the agent actually answers, not by a blanket rule: `not_consumed` when the holder
still held the turn and refused before writing, `started_new_turn` when the agent says it opened a
separate turn instead, and `unknown` when it answers nothing, answers something unrecognized, or the
turn settles while the text is being written. Nothing is ever silently resent.

### The composite (`--steer-mode interrupt`)

It reuses `cancel` and `send` on the same session and adds no scheduler, no second lifecycle and no
retry. In order: snapshot the running turn, `session/cancel`, wait for it to actually settle, then
send the text **once** as the next turn. Because it is the same ACP session, the next turn still has
the whole conversation.

- The cancelled turn keeps its own request id and terminal state (`cancelled_turn_request_id`,
  `cancelled_turn_stop_reason`); the steering text runs under a new `new_turn_request_id`.
- `side_effects_possible` is true when the interrupted turn may already have written files or run
  commands. Interrupting is not undoing.
- If the cancel is **not** confirmed, nothing is sent: the outcome is `unknown` with
  `steer-cancel-unconfirmed`, so a turn that refuses to stop can never receive a second dispatch.
  Verify with `observe` before deciding; the Runner does not retry.
- If the turn had already ended - before the call, or on its own in the moment between the decision
  and the cancel - no cancel is sent, and the receipt says `resent_without_interrupt` with
  `cancel_sent: false` rather than claiming an interruption that never happened.
- The cancel is bound to the exact turn this steer targeted, and every fact reported about that
  turn is read while it is still held - turns also start from worker events, on another thread, so
  `the turn running now` is not the same question as `the turn we cancelled`. If the target is
  replaced, the outcome is `unknown` with `steer-turn-changed` and the steering text is **not**
  sent. `cancel_sent` then says whether a cancel had already gone out: `false` means nothing was
  cancelled at all, `true` means the target was asked to stop and the outcome of that request is
  unconfirmed - read `side_effects_possible` with it. The Runner never interrupts a turn the Agent
  did not target, and never reports one turn's cancel under another's id.
- The text is sent at most once. A send that fails after a successful cancel reports
  `steer-send-failed` and is not resent here.
- `--cancel-timeout SECONDS` bounds the wait for the old turn to settle; without it the op's own
  `--timeout` applies. How fast a cancel settles is a platform fact, so a timeout shorter than this
  platform's real cancel latency buys a truthful `unknown`, not a faster steer.

