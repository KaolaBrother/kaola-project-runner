# Issue #70 — internal recovery of the sole unbound worker, live (2026-09-18)

The previous candidate made the outer Agent the normal recovery path for an unbound worker. Under
the confirmed four-layer boundary that is wrong: ZCode schedules its own workers through Project
Runner, and the delegating Agent does not take over read/rebind session by session. This run proves
the Runner can do it internally with operations it already has, so the guidance needs no new
mechanism.

Candidate `62a4ef2143efca5afa935ef3e2211a89ced64720` (rebased onto `main` 464c4f9); the run itself
used the same working tree, committed unchanged as that SHA. Fresh sandbox
`/tmp/kw-i70-live4/project`, candidate Skills copied there, the installed dispatch reference
byte-compared to the candidate's. Raw evidence: `evidence/live-internal/00…16`.

## Leg A — the in-flight turn had already finished (`01`–`06`)

Worker `codex-i70d-w1` started **unbound** by me, a task dispatched `--no-wait` (anchor 6), then a
fresh Host was told: this is your only worker and your only notifier, no timer, no other source, and
I will not read or rebind it for you.

The Host, acting on the reference alone: `observe` → `heartbeat_host: null` with
`heartbeat_host_known: true` ("truly unbound — it can never wake me") and `turn_active: false`, so
it said plainly that **no bounded wait was needed** and read the reply from the dispatch anchor;
verified the delivery on disk; then at the safe idle point exact `stop` (`stopped: true`, exit 0,
`residual_pids: []`), `start` again with `KAOLA_ACP_HEARTBEAT_HOST` plus `--resume`, and verified
the in-force `heartbeat_host` — "mine, not just requested". It then dispatched the follow-up
`--no-wait` (anchor 446), wrote the heartbeat prompt and ended the turn.

The restored loop then ran by itself (`06`): the worker's turn end produced a real
`kaola-host-notify/1` beat, the Host confirmed the fingerprint, read from anchor 446, verified the
file on disk, accepted, and exact-stopped the worker. The Host's event log ends with three
`worker_event` / `worker_event_delivered` / `worker_event_confirmed` triples — the event path is
genuinely back.

## Leg B — the task was genuinely still running (`07`–`13`)

To exercise the bounded read itself: `codex-i70d-w2` started **unbound**, a longer task dispatched
`--no-wait`, and `09` captured it mid-turn (`turn_active: true`, `activity_hint: busy`). The Host
was then given the same situation and acted:

1. `observe` — unbound (`heartbeat_host: null`, known), turn live, running fingerprint recorded.
2. **`wait --timeout 300`** — *"With nothing bound, ending my turn would wait on nothing, so this
   one bounded call is the reference's recovery exception (explicitly 'never the ordinary wait,
   never a poll loop' — one call, one deadline, no repetition)."* Returned inside the bound:
   `outcome: turn_completed`, `stop_reason: end_turn`, `mutation_status: completed`.
3. `observe` — same fingerprint as the running turn, now finished.
4. `capture --since 6` — the reply from the dispatch anchor, "not from the wait's cursor 620";
   verified against the file on disk (25 lines, line 13 as reported).
5. `stop` — `stopped: true`, exit 0, `residual_pids: []`.
6. `start … --resume <native id>` with the binding variable on that one command.
7. `observe` — the **running holder** reports `heartbeat_host` naming the Host
   (`13-worker2-bound-observe.json` confirms it independently).

Nothing was cancelled, nothing re-sent, no timer or poll loop added, and no per-worker duty was
pushed outward. One incidental fact worth keeping: while the Host was mid-beat, my own `send` to it
was refused with `prompt-in-progress` and dispatched nothing (`11`) — the admission path, not a
special case.

## Close-out

Exact stops for both sessions (`14`, `16`): `stopped: true`, `agent_exit_code: 0`,
`residual_pids: []`; no `i70d` process left. Issues #67, #71, #72 and the VRPCadCore sessions were
untouched.

## What is still only documented, not lived

The failure branch — the bounded read hitting its deadline, or the rebinding `start` refusing, so
the Host reports an exception and the decision it needs. Both legs here completed inside the bound,
which is the honest outcome of a real run; the contract suite pins the wording of that branch.
