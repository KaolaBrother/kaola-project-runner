# Issue #81 — Mission 1: #65 steer receipt contract + current steer surface (read-only)

Date: 2026-09-19. All facts below are read from the current `main` checkout
(`f6cbe27`) — the version #79 is also based on — plus the archived #65 run
records. Nothing was edited; no process was started.

## The #65 receipt contract (the vocabulary a v4 path must speak)

Source: `kaola-workflow/archive/issue-65/finalization-summary.md` and
`scripts/kaola-acp-holder.py::op_steer` (lines 2156-2326).

Every steer receipt carries:

- `steer_outcome`: `injected` | `written` | `interrupted_and_resent` |
  `resent_without_interrupt` | `started_new_turn` | `not_consumed` |
  `unsupported` | `rejected` | `unknown`
- `steer_consumed`: `true` | `false` | `null` (null = undecided)
- `steer_confirmation`: `agent-confirmed` | `write-only` | `cancel-confirmed` |
  `no-turn-to-interrupt` | `none`
- `steer_method`, `steer_mode` (`native`|`interrupt`), `steer_request_id`,
  `steer_native_outcome`, `steer_native_reason`, `steer_response`
- turn attribution: `turn_request_id`, `turn_request_id_after`,
  `turn_request_id_preserved`, `turn_prompt_fingerprint`, `turn_active`
- `mutation_performed`: true only for `injected`/`written`/`started_new_turn`;
  false for clean refusals; null for `unknown`
- `error.code`: `steer-unsupported`, `steer-empty`, `steer-no-response`,
  `steer-rejected`, `steer-write-only-confirmation`, `steer-started-new-turn`,
  `steer-prompt-required`, `steer-undecided`, `steer-unrecognized-outcome`,
  `steer-turn-changed`, `steer-cancel-unconfirmed`, `steer-send-failed`,
  `steer-mode-required`, `steer-capability-unknown`,
  `steer-unsupported-transport`, `steer-holder-outdated`

Hard rules the contract already pins (from `op_steer` and the #65 summary):

1. `queued`/`startedNewTurn` is NEVER reported as `injected` — `startedNewTurn`
   maps to `steer_outcome: started_new_turn` with its own error code.
2. A write that cannot be confirmed consumed is `written`/`write-only` or
   `unknown` — never upgraded to `injected`.
3. An idle session steer is refused BEFORE writing (`not_consumed` /
   `no-active-turn`); some agents manufacture a detached turn on an idle steer
   call, which is exactly the false-positive shape #81 must not reproduce.
4. Timeout/lost reply → `unknown`, "do not resend blindly".
5. Turn-end race: `turn_request_id` snapshot vs after, `turn_request_id_preserved`
   reported; a replaced turn is never impersonated (`steer-turn-changed`).
6. `-32601` from the agent maps to `steer_outcome: unsupported`; other JSON-RPC
   errors map to `rejected`.
7. `mutation_status` from the live turn is echoed into the receipt.

## The wire shape the holder sends (what an adapter-side native entry receives)

`op_steer` issues ONE request to the agent process:

```json
{
  "method": "<acp_steer_method from platforms/*.yaml>",
  "params": {
    "sessionId": "<acp session id>",
    "prompt": [{"type": "text", "text": "<agent-selected steer text>"}],
    "_meta": {"steering": {"idleBehavior": "promptRequired"}}
  }
}
```

It then interprets `result.outcome` — `injected` | `written` | `startedNewTurn`
| `promptRequired` | `unknown` — plus optional `result.confirmation` and
`result.reason`. Any other result key set is tolerated (`steer_native_*` fields
record it); an unrecognized outcome string maps to `unknown`, never to a pass.

## The routing layers (where a v4 steer would slot in)

- `scripts/kaola-tmux.sh` — `steer` command; refuses `pty` transport outright
  (`steer-unsupported-transport`); passes `--steer-mode` / `--cancel-timeout`
  to `kaola-acp.py`. No platform knowledge.
- `scripts/kaola-acp.py` (lines 1685-1773) — reads `acp_steer_method` and
  `native_steering` from the platform manifest. Default mode: `native` iff a
  method is configured. No method + no mode → `steer-mode-required` refusal
  advertising `available_steer_modes: ["interrupt"]`. `--steer-mode native`
  with no method → `steer-unsupported` / `steer-capability-unknown`. Dispatches
  holder op `steer` (native) or `steer_interrupt` (composite).
- `scripts/kaola-acp-holder.py` — `op_steer` (native, above) and
  `op_steer_interrupt` (cancel → confirm settled → resend once; honest
  `interrupted_and_resent` / `resent_without_interrupt` / `unknown`).
- `scripts/kaola-zcode-acp.py` — the Runner-owned ACP translator over
  `app-server --stdio`. Client-facing route table at line ~1529:
  `session/new|load|resume|list|prompt|cancel|close|set_mode|set_config_option`,
  `initialize`, `authenticate`. Backend calls used: `session/create`,
  `session/subscribe` (`deliveryKind: desktop-continuous`), `session/read`,
  `session/send`, `session/stop`, `session/close`, `session/setMode`,
  `session/setModel`, `session/setThoughtLevel`, `session/resume`,
  `session/list`. Backend→client requests bridged:
  `interaction/requestPermission`, `interaction/requestUserInput`,
  `session/requestRuntimePreferences`. Backend events arrive as
  `session/event` notifications `{sessionId, type, payload}`; translated types
  today: `model.streaming`, `tool.updated`, `session.updated`,
  `turn.completed`, `turn.failed`, `turn.terminal`.
- `platforms/zcode.yaml` — `native_steering: "unsupported"`,
  `acp_steer_method: ""`, `steering_summary` documents the 0.16.5 engine-vs-
  protocol finding and the `--steer-mode interrupt` + long cancel window path.

## Minimal-change shape this suggests (hypothesis for M5, not a verdict)

If the v4 path proves real, the smallest integration that keeps every existing
contract is: the adapter serves one new client-facing steer entry (e.g.
`_session/steering`) that internally performs the proven v4 sequence
(CAS `setFollowupMode=guide` + `v4/command sendText`) and returns
`{outcome: injected|written|startedNewTurn|promptRequired|unknown, confirmation,
reason}` in exactly the shape `op_steer` already interprets — then
`platforms/zcode.yaml` sets `acp_steer_method` + `native_steering` with the
version evidence. Holder, `kaola-acp.py`, `kaola-tmux.sh`, and the receipt
schema stay untouched; `--steer-mode interrupt` remains for old versions and
as fallback. Whether v4 steer events (`turn.steerQueued`/`turn.steerDrained`)
arrive on the existing `session/event` stream is a live-measurement question
for M4.

## Isolation note

`kaola-zcode-acp.py` is owned by the in-flight #79 run (its worktree holds the
3.12.3 bootstrap). This file records reads only. Phase-1 evidence and probe
code live under `kaola-workflow/issue-81/evidence/` and `/tmp`; no production
file, generated Skill, or #79 artifact is touched.
