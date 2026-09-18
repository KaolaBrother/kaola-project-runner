# Issue #70 — the sole unbound in-flight worker: hand-off or blocked (2026-09-18)

The outer review found a real hole in the recovery guidance at `a193d3c`: step 2 told a Host to
record the read-back duty in its heartbeat body and end the turn normally. If the unbound worker
is the Host's **only** wake source, that file write starts nothing — the Host waits forever, which
is the very lifecycle failure this Issue exists to fix.

Fix (guidance only, no timer, no poll loop, no rebind API, nothing cancelled): before ending the
turn the Host hands the read-back and safe-rebind duty to the outer controlling Agent, naming the
session and the anchor; with no outer Agent and no other confirmed wake source it reports itself
**blocked**, with the entry point for resuming, instead of claiming a wait it does not have. The
startup reference states the receiving side: that duty is the outer Agent's, and a Host reporting
itself blocked stays blocked until the outer Agent acts.

## The live scenario

Fresh sandbox `/tmp/kw-i70-live3/project`, candidate Skills copied there and byte-compared to the
candidate's own reference. Raw evidence: `evidence/live-handoff/00…09`.

1. `codex-i70c-w1` started **unbound** (`01`: `heartbeat_host: null`, `heartbeat_host_known: true`).
2. A real task dispatched to it `--no-wait` (`02`: `outcome: in_progress`, `dispatch_event_cursor: 6`)
   — genuinely in flight.
3. Host `zcode-i70c-host` started (`03`), then one read-only prompt (`04-prompt.txt`) stating the
   truth of the situation: that worker is the only session that could ever notify it, no timer, no
   second worker, no other event source. Question: you are about to end this turn — what must you
   do first, and what if no outer Agent exists at all?

## What the Host answered (`05-host-reply.json`, full text `06-host-reply-full.txt`)

- With an outer Agent: confirm the binding *in force* first (`heartbeat_host_known` plus
  `heartbeat_host` naming it, "a receipt's `heartbeat_host_requested` is only a request"), and
  because this worker is its only possible notifier, "an unverified binding here means I am not
  reliably event-driven, and that must be resolved *this beat* — verify now, or hand the duty to
  the outer Agent in this reply — never discovered after the turn ends."
- Without one: **"I am BLOCKED"**, quoting the new rule, and then: "I do not pretend the heartbeat
  recording wakes anyone — writing it in the body starts nothing … my final reply *is* the handover
  record: it must state BLOCKED plainly and carry the full entry point for resuming — which session
  to read (`codex-i70c-w1`), from which anchor (dispatch event cursor 6 … with the fingerprint
  check), that this beat's continuation depends on someone resuming me, and that the binding is to
  be redone at the next safe idle point." It keeps the in-flight work — "cancel nothing" — and
  holds no turn open: "there is no wait I actually have".

It answered on the delivered text, not on prompting: the prompt never mentioned blocking,
hand-off, or the heartbeat file.

## Confirming the stall is real, not theoretical

The worker's dispatched turn completed normally (`07`: `turn_completed`) and the Host's event log
contains **zero** `worker_event` entries — the completed turn of an unbound worker woke nobody, so
"record it and end the turn" would have left this Host parked indefinitely.

## Close-out

Nothing was cancelled: the in-flight task ran to completion before cleanup. Exact stops (`08`,
`09`): both `stopped: true`, `agent_exit_code: 0`, `residual_pids: []`, no `i70c` process left.
Issues #67, #71, #72 and the VRPCadCore sessions were untouched.
