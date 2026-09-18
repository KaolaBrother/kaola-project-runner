# Issue #65 — isolation live acceptance (inner ZCode Worker + Codex Worker)

Bound to candidate **`68845bd7ef6c746cfde219d4d87b8cb670d5fce6`** (the `main` at measurement time).
Run 2026-09-18 16:03–16:16 local. At measurement time, this evidence was
unarchived and under the project's ignored `.kw/`; it was archived later
without rerunning the probe.

Scope: only the part of Issue #65's acceptance that had contract coverage but no
live evidence. Nothing here claims #69, and #69 is untouched.

Setup: Skills installed **from this candidate** into the scratch repo
`.kw/verify-65-isolation/repo/.zcode/skills` with
`install-local.sh --skills-dir … --method copy --platform zcode,codex` — no
global install. Sessions: Host `zcode-kaola-i65iso-host` (ZCode 0.16.5), inner
worker `zcode-kaola-i65iso-inner` (**ZCode**), worker
`codex-kaola-i65iso-codex` (**Codex**; model requested vs actual below). The Host was given one
bootstrap prompt (its own identity, where the Skills are, the two tasks, and
"follow the Skill for how to wait"); everything else came from the generated
Skill.

## What was proven live, and by what

### 1. One Host, two workers of different platforms, woken by both — live

Host holder event log (`evidence/host-events.jsonl`, verbatim cursors):

| cursor | event |
|---|---|
| 287 | `worker_event` staged — `codex/codex-kaola-i65iso-codex/idle/22`, `outcome=turn_completed stop_reason=end_turn` |
| 288 | `worker_event` staged — `zcode/zcode-kaola-i65iso-inner/idle/18`, same shape |
| 319 | `worker_event_delivered` — **both ids in one delivery**, at the turn boundary |
| 486 | `worker_event` staged — `zcode/zcode-kaola-i65iso-inner/terminated/19`, `exit_code=0` |
| 564 | `worker_event_confirmed` — both `idle` ids, after that beat completed |
| 565 | `worker_event_delivered` — `terminated/19` |
| 642 | `worker_event_confirmed` — `terminated/19` |

This is the multi-worker case the issue asked for: two workers on **different
platforms**, one of them an **inner ZCode worker**, both binding the same Host
and both waking it. Cursors 287/288 → 319 also show two events staged while the
Host turn was active and **batched into a single delivery** — the same behaviour
`test-zcode-heartbeat-contract.py::test_bounded_queue_dedup_and_single_batch_flush`
asserts offline, now observed on real CLIs.

### 2. The Host read each worker's real reply, from the dispatch anchor

In its own words (`evidence/host-transcript.txt`):

> "The notification isn't the reply, so I'll now read each worker's real reply
> through its own Skill: `observe` to confirm the fingerprint matches my dispatch
> and the turn finished, then `capture --since` from each **dispatch** cursor
> (8 inner, 6 codex — not the event cursors)."

- inner ZCode: fingerprint `sha256:311f0c…83ea` matched, `end_turn`, reply
  exactly `JADE-INNER-65`.
- Codex: fingerprint `sha256:6198ca…046a3` matched, `end_turn`, one terminal
  `tool_call` for `sh -c 'exit 7'` followed by exactly `JADE-CODEX-65` / `7`.

### 3. Exact-stop of the inner worker reached only the inner worker

After the Host stopped **only** `zcode-kaola-i65iso-inner`, the three status
receipts taken by me, independently of the Host's prose
(`evidence/{3-host,4-inner,5-codex}-status.json`):

| session | state | agent_alive | holder pid | agent pid |
|---|---|---|---|---|
| Host `zcode-kaola-i65iso-host` | `ready` | `true` | 8339 (unchanged since start) | 8340 |
| inner `zcode-kaola-i65iso-inner` | **`stopped`** | — | — | — |
| Codex `codex-kaola-i65iso-codex` | `ready` | `true` | 9296 | 9297 |

Three distinct holders and holder instance ids. The inner stop reached neither
the Host nor the sibling worker. This is the live counterpart of
`test-zcode-host-contract.py::test_nested_two_layer_isolation_and_exact_stop`,
which asserts the same separation against **fake** ZCode entries.

### 4. The exit event, and that it arrives at a turn boundary

The inner stop produced `terminated/19` with `exit_code=0`, staged at cursor 486
while the Host was still working and delivered at 565 — its next turn boundary.
The Host said so before it happened and then handled it idempotently:

> "What event the stop produced for me: **none within this turn — and by design
> none can.** Worker events are never injected mid-turn; they stage and deliver
> at my next turn boundary."

and on the next pass:

> "a fresh status read confirms `zcode-kaola-i65iso-inner` remains
> `state: stopped` … The delivery is already accepted and recorded; nothing to
> re-do."

`exit_code=0` on the event matches `agent_exit_code: 0` on the stop receipt.

## Model: requested vs actual (correction)

An earlier draft of this file said the Codex worker ran "gpt-5.6-sol high". That
was taken from the Host's own prose ("GPT-5.6 Sol High per runner default"),
which restates the **manifest default label**, not the session's actual model.
The receipt says otherwise, so both are recorded from the raw evidence:

| | Value | Source |
|---|---|---|
| requested | nothing explicit — no `--model`, `--effort` or `--tier` was passed, so the Runner's manifest default applies: `default_model_id: "gpt-5.6-sol"`, `default_model_effort: "high"` (`platforms/codex.yaml:18-21`) | the dispatch command in this run + the manifest at `68845bd` |
| actual | **`gpt-5.6-luna[max]`** | `evidence/5-codex-status.json` → `session_meta.models.currentModelId` |

`gpt-5.6-sol[high]` is present in that receipt's `availableModels`, so the
difference is not an unavailable model. This run does not diagnose why the
session reports `luna[max]`, and nothing here was re-run for it: the isolation
findings above do not depend on which Codex model answered. Recording it as the
project's rule requires — a model observation is evidence, never a gate — and
leaving the cause open.

## What this run does NOT prove

Stated precisely, so the record is not read as more than it is:

- **No `turn_failed` was produced.** The "controlled harmless failure" was a
  worker tool call exiting non-zero (`sh -c 'exit 7'`), which the worker reported
  inside a turn that still ended `end_turn`. That exercises a failing command and
  the worker's honest report of it — it does **not** exercise a failed ACP turn
  or a crashed agent. A worker `turn_failed`/`process_exited` path remains
  covered only by `test-zcode-heartbeat-contract.py` and
  `test-zcode-host-contract.py`, offline.
- **Resume redelivery of unconfirmed events was not exercised** here: no holder
  was restarted mid-flight. It stays covered by
  `test_resume_redelivers_unconfirmed_events` (offline) — this run only shows
  staging, batched delivery and confirmation.
- **Dedup** is shown only in its batching form (two ids, one delivery). The
  bounded-queue dedup of *repeated* events remains offline-covered.
- Issue #66's two earlier Host live rounds proved the ordinary single-Codex-worker
  loop and the startup receipt; they did not cover an inner ZCode worker, which
  is what this run adds.
- **The Codex model question above is not investigated.** Whether the Runner
  applied its manifest default, or the CLI session carried a previously selected
  model, is unexamined here.

## Isolation and cleanup

Every session here was created and exact-stopped by this run:
`codex-kaola-i65iso-codex` (`stopped: true`, exit 0, `residual_pids []`) and
`zcode-kaola-i65iso-host` (`stopped: true`, exit 0, `residual_pids []`); the
inner worker was stopped by the Host with the same clean receipt. No
`i65iso` holder or agent process remains. Nothing outside
`.kw/verify-65-isolation/` was written: no repository file, no archive, no push,
no issue change, no global install, and the pre-existing sessions
(`*-vrpcadcore`, `claude-code-kaola-issue68-0918`, tmux `kaola-9d0873b0`) and the
issue-68 run were never touched.

## Files

- `evidence/CANDIDATE_SHA` — `68845bd…`
- `evidence/0-install.txt` — workspace install transcript
- `evidence/1-host-start.json`, `2-host-dispatch.json` — Host start and the
  non-blocking dispatch receipt (`dispatch_event_cursor: 8`)
- `evidence/3-host-status.json`, `4-inner-status.json`, `5-codex-status.json` —
  the isolation evidence after the inner stop
- `evidence/6-codex-stop.json`, `7-host-stop.json` — exact stops
- `evidence/host-events.jsonl` (642 events) — the full carrier chain
- `evidence/host-transcript.txt` — everything the Host said
- `evidence/heartbeat-prompt.json` — the file the Host maintained
