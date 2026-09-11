# PoC report — Runner v2 ACP transport (issue #15)

Date: 2026-09-11 · Branch: `workflow/bundle-15` · Design: `docs/runner-v2-dual-transport-design.md` v0.2

## Verdict

**Part A green** (offline contract, 13/13), **Part B green** for Grok and Kimi
(11/13 scenarios live each; #2 not triggerable on either platform, #6
precondition absent), **Part C measured**: ~**12× fewer bytes** and
~**12× fewer cl100k tokens** handed to the orchestrator, ~2× fewer Runner
invocations, ~1.7× faster end-to-end. The design proceeds to implementation;
the open question is permission gating (see findings).

## What was built (PoC scope, not wired into installer/manifests)

| file | role |
|---|---|
| `scripts/kaola-acp.py` | socket-client CLI: `preflight start send wait observe capture permit key cancel stop status` |
| `scripts/kaola-acp-holder.py` | per-session holder (§3.3/§7): spawn `start_new_session`, NDJSON JSON-RPC, reader + stderr threads, pending-permission map, five-state `mutation_status`, §7.6 stop sequence, record dir §3.2 + `events.jsonl` |
| `tests/contract/mock-acp-agent.py` | scriptable mock ACP agent (12 scenarios) |
| `tests/contract/test-acp-contract.py` | offline contract suite, wired into `validate.sh` |

Receipts: `schema_version: 3` + `transport` block + `mutation_status` +
`stop_reason` + `pending_permissions` + `event_cursor`; `final_text` capped at
4000 chars; `capture` levels L0–L3 implemented.

## Part A — offline contract (all 10 issue branches green, 13 tests / ~17s)

- [x] agent dies while a permission request is pending → `outcome: process_exited`, `mutation_status: accepted` (write boundary held)
- [x] stdout half line / non-JSON line → reassembled/counted, turn completes
- [x] stderr floods the pipe (1 MiB) → no deadlock, `end_turn`
- [x] `session/cancel` races `end_turn` → first stopReason wins, `completed`
- [x] `$/cancel_request` cascade → own permission dropped from `pending_permissions`; prompt request cancelled → `-32800` surfaced as `turn_canceled`
- [x] `protocolVersion: 2` → `acp-protocol-version-unsupported`, no live agent
- [x] `fs/*` / `elicitation/create` / unknown → `-32601` each, no hang
- [x] numeric-string response id → lenient match, works end-to-end
- [x] 3 concurrent permission requests → all in `pending_permissions`, `permit --request-id` answers each; bare `permit` → `request-id-required`
- [x] `stop` leaves `residual_pids: []` incl. a SIGTERM-ignoring child (`stubborn_child` scenario, process-group kill + scan)
- [x] happy path: `final_text`, `stop_reason`, `context_usage`, `event_cursor`
- [x] `send` during active turn → `prompt-in-progress`

## Part B — live receipts

Full per-scenario evidence: `kaola-workflow/bundle-15/evidence/part-b-grok.md`,
`part-b-kimi.md`. Highlights:

| scenario | Grok 1.0.25 | Kimi 0.41.0 |
|---|---|---|
| 1 prompt→end_turn | PASS (`final_text`, 3.2s) | PASS (9.4s, `context_usage` 22113/1M) |
| 2 permission→permit | **not triggered** — `always-approve`, 0 `request_permission` events | **not triggered** — `mode=default` claims manual approvals but none emitted |
| 3 timeout→cancel | PASS `prompt_timeout`→`cancelled` | PASS |
| 4 stop→residual [] | PASS, `agent_exit_code 0` on stdin EOF | PASS, same |
| 5 resume/continue | `session/load` + context retained (PONG recall); `continue-unsupported` | same |
| 6 login_required | PRECONDITION-NOT-MET (`login_required:false`, authMethods reported) | same |
| 7 spawn-fail→not_started→pty | PASS (`acp-initialize-failed` → `not_started`/`mutation_performed:false`; pty resend PONG-PTY) | PASS (same code path; pty leg verified under Grok) |
| 8 duplicate/transport-mismatch | PASS `duplicate-prompt-warning` (prev transport/status) + `transport-mismatch` vs live pty | PASS (duplicate) / shared code path |
| 9 prompt-in-progress | PASS | PASS |
| 10 holder kill→unknown→force-clean | PASS `holder_lost`,`mutation_status:unknown`,residual [] | PASS |
| 11 non-canonical --repo | PASS identical refusal as v1 | PASS |
| 12 same name, 2 repos | PASS separate records | PASS |
| 13 configOptions ids | `model`={grok-4.6,grok-4.5}; `reasoning_effort`={xhigh,high,medium,low} | `model`={kimi-for-coding, -highspeed, k3, k3-256k}; `thinking`={low,high,max}; `mode`={default,plan,auto,yolo} |

## Part C — token cost (same task: "reply PONG", 5 runs each, medians)

| metric | acp | pty | acp/pty |
|---|---|---|---|
| bytes to orchestrator | **2,453** | 29,982 | **12.2× less** |
| cl100k tokens | **791** | 9,313 | **11.8× less** |
| Runner invocations | 3 | 6 | 2× fewer |
| observation reads | 0 | 3 | polling eliminated |
| wall time | 7.9 s | 13.1 s | 1.7× faster |
| recovery attempts | 0 | 0 | — |
| task success | 5/5 | 5/5 | equal |
| `mutation_status` accurate | yes (all runs) | n/a | — |

Method: `kaola-workflow/bundle-15/evidence/measure.py`; raw data
`part-c-raw.json`. pty bytes dominated by `observe` frames (≈9–10 KB JSON each
incl. `raw_current_frame`); the acp `send --wait` receipt is a single ~2 KB L0.

## Findings that shape v2 implementation

1. **Permission flow is currently unexercised live.** Both CLIs auto-approve
   over ACP at observed defaults (Grok `always-approve`; Kimi `mode=default`).
   The `permit`/`pending_permissions` machinery is mock-verified only. Before
   defaulting acp for the other four platforms, verify whether any CLI emits
   `session/request_permission` under a stricter mode (`mode` configOption on
   Kimi; Grok exposes no approval configOption).
2. `session/load` works on both; `session/list`, `session/resume`,
   `session/close` are absent on both → `--continue` reports
   `continue-unsupported`; resume path should use `session/load` (v0.2 already
   allows either).
3. Grok omits `agentInfo` and `usage_update`; Kimi emits both.
   `session_info_update` is a Grok-only variant (handled as unknown).
4. Cross-transport `duplicate-prompt-warning` needs the pty path to journal
   `last_prompt` into the shared record — production wiring item; acp-side
   warning verified.
5. Socket path must stay short (AF_UNIX ~104 B on macOS): holder binds at
   `$TMPDIR/kaola-<uid>-acp/<hash>.sock`, `holder.sock` in the record dir is a
   symlink.
6. `configOptions` lands on `session/new` result → `session_meta` recorded;
   manifest candidates: Grok `model`/`reasoning_effort`, Kimi
   `model`/`thinking`/`mode`.

## Exit criteria status

- `validate.sh` + `render-skills.py --check`: green (incl. new acp suite). ✅
- Part A fully green. ✅
- Part B: Grok + Kimi — all applicable scenarios green; #2 not triggerable at
  observed defaults (documented), #6 precondition absent (auth already cached). ✅
- Part C: medians published above. ✅ — input for the four-platform
  default-transport decision is ready.
