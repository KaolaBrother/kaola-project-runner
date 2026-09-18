# Issue #70 — minimal live re-proof on the delivered Host guidance (2026-09-18)

Why this exists: the full live loop (`live-2026-09-18.md`) ran against reference text that was
later rewritten to restore the sentences the Issue #65 contract pins. The ACP scripts are
byte-identical across that rewrite, so the mechanism evidence carries over unchanged; what
needed re-proving is only that the **delivered wording** still makes a real ZCode Host reach
the same verdicts.

Delivered candidate `a193d3c12d9080e2b751be6786df753072683656` (rebased onto `main` b229f84).
Fresh isolated sandbox `/tmp/kw-i70-live2/project`, candidate Skills copied there
(`install-local.sh --method copy --platform zcode,codex`); the installed
`references/zcode-host-dispatch.md` was byte-compared to the candidate's and is identical.
No global install, no other session touched.

## What was run (read-only for the Host)

1. Worker `codex-i70b-w1` started by me **unbound** (`01`): `heartbeat_host: null`,
   `heartbeat_host_known: true`.
2. Fresh Host `zcode-i70b-host` started (`02`).
3. One prompt (`03-prompt.txt`), explicitly read-only — no dispatch, no rebind, no stop —
   asking three questions: is the adopted worker bound to you, what recovery would you run,
   and what would you conclude from a receipt with no binding information at all.

## What the Host answered (`04-host-reply.json`, full text `05-host-reply-full.txt`)

- It ran `observe` on the adopted worker itself and answered **"No — the binding is not in
  place"**, quoting `heartbeat_host_known: true` as "a positive, current fact, not an unknown
  from an older record (which would be `false`)" and `heartbeat_host: null` as "the binding
  actually in force on the running holder … not a request (`heartbeat_host_requested` would be
  only the request)".
- Recovery, in the reference's order: keep in-flight work and cancel nothing; carry the
  read-back duty in the heartbeat body; rebind only at a safe idle point with exact `stop` then
  `start` with the variable on that one command, then verify the new receipt's `heartbeat_host`
  (with `--resume` where supported). Explicitly **not** done: repeating `start` or attaching the
  variable to a later `send` ("a repeat `start` on a live holder yields `session-exists` and
  binds nothing"), exporting it globally and calling it bound, auto-cancelling, re-sending
  unproven work, switching platform, or stopping/sleeping/polling to manufacture a wake-up.
- On absent binding information: "unknown, and treat it as unbound … absence is never evidence
  that it will wake me", while distinguishing it from the positive `null`.

## Close-out

Exact stops (`06`, `07`): both `stopped: true`, `agent_exit_code: 0`, `residual_pids: []`; no
`i70b` process remained. The nine unrelated live Runner sessions (Issues #67, #71, #72 and
VRPCadCore) were alive before and after and were not touched.

## Difference from the full live run

The delivered reference differs from the live-read version only in: the three-identities table
returning to this file, the outer-Agent section becoming a pointer to `host-startup.md` (which
gained "a Host that returns `end_turn` has finished that beat, not the project" and the
instruction to read the dispatch reference before the first dispatch), the Issue #65 pinned
sentences restored verbatim, and small wording tweaks inside the two Issue #70 sections
(heading, "reused and adopted workers", two bullets merged). This re-proof covers exactly the
part that carries the Issue #70 behaviour; the event-loop mechanism itself is unchanged code
and remains proven by the full run.
