# Issue #65 — ACP steering across the nine Worker platforms

Measured on 2026-09-18 on this Mac, against the real installed CLIs.

**Scope: the ACP channel only** (owner scope correction, 2026-09-18). PTY/TUI and
other non-ACP channels are not investigated here and their absence blocks
nothing; `steer` answers `steer-unsupported-transport` over `pty`.

Every row separates four different things:

- **native** — whether the platform's own ACP surface has a mid-turn entry;
- **usable path** — what the Agent can actually run today, native or composite;
- **live** — the end-to-end proof through the generated Skill's own script;
- **evidence** — version and reproducible observation.

Native probe: `evidence/probes/steer_probe.py`. Phase 1 (idle) calls four
candidate entries — `_session/steering`, `session/steering`, `session/steer`,
`_session/steer` — carrying `_meta.steering.idleBehavior = "promptRequired"`;
`-32601` means the entry does not exist. Phase 2 (`--live`) steers a real
tool-using turn while it is demonstrably running. Raw receipts: `evidence/idle/`,
`evidence/fallback/`, `evidence/live/`. A `-32601` on one method name is not a
verdict: each row rests on all four entries, the `initialize` advertisement, a
live second-message observation, and — for Claude Code and ZCode — the runtime's
own code.

Live steering matrix: `evidence/probes/live-steer-matrix.sh`, receipts in
`evidence/live-matrix/`. Per platform it starts a session, dispatches a first
prompt carrying the codeword `TOPAZ-65` plus a ten-step shell loop, waits ~25 s
until the turn is demonstrably working, steers (native or `--steer-mode
interrupt`), waits for the steered turn, and requires the final text to contain
the codeword — so a pass proves the old turn ended, the new instruction ran, and
**the same ACP session kept its context**.

## Matrix

| Platform | Native steering (ACP) | Usable path today | Live result | Version |
|---|---|---|---|---|
| Claude Code | **supported** — `claude --input-format stream-json` stdin, bridged as `_session/steering` | `steer` (native) | **PASS** — `written` / `write-only`, `turn_request_id` 7 → 7 preserved, the running turn absorbed it and ended `end_turn` with `…Step 3 done…TOPAZ-65-OK` | cli 2.1.272; bridge rebuilt from vendored sources |
| Codex | **supported** — `_session/steering`, advertised `_meta.steering.supported=true` | `steer` (native) | **PASS** — `injected` / `agent-confirmed`, `turn_request_id` 7 preserved, `end_turn` with `TOPAZ-65-OK` | cli 0.153.4 / adapter 1.11.0 |
| Cursor CLI | unsupported | `steer --steer-mode interrupt` | **PASS** — `interrupted_and_resent`, cancelled turn 6 → new turn 7, final `TOPAZ-65-OK` | 2026.09.10-fd3934a |
| Devin | unsupported | `steer --steer-mode interrupt` | **PASS** — `interrupted_and_resent`, 5 → 6, final `TOPAZ-65-OK` | cli 3000.10.21, agent affogato 0.0.0-dev |
| Droid | unsupported | `steer --steer-mode interrupt` | **PASS** — `interrupted_and_resent`, 5 → 6, final `TOPAZ-65-OK` | @factory/cli 0.220.0 |
| Grok | unsupported | `steer --steer-mode interrupt` | **PASS** — `interrupted_and_resent`, 5 → 6, final `TOPAZ-65-OK` | cli 1.0.25 |
| Kimi CLI | unsupported | `steer --steer-mode interrupt` | **PASS** — `interrupted_and_resent`, final `TOPAZ-65-OK` | Kimi Code CLI 2.0.0 (cli 0.41.0) |
| ZCode | unsupported on the protocol surface; engine-capable | `steer --steer-mode interrupt --cancel-timeout 180` | **PASS** — `interrupted_and_resent`, 4 → 5, final `TOPAZ-65-OK`; needs a long cancel window (below) | cli 0.16.5 |
| OpenCode | unsupported | `steer --steer-mode interrupt` | **PASS** — `interrupted_and_resent`, 3 → 4, final `TOPAZ-65-OK`; needs a working network path for session bootstrap (below) | 1.18.31 |

No row is `unknown`: every platform was reached and answered, and **all nine are
proven live end to end** — the old turn ended, the new instruction ran, and the
same ACP session returned the codeword from the first prompt.

### OpenCode needs a working network path, not a different version

OpenCode's `session/new` bootstrap makes a network call. Behind the proxy this
shell exports (`HTTP_PROXY`/`HTTPS_PROXY`) that call times out and OpenCode
reports the whole session creation as `-32603 {service: "directory"}`, so `start`
fails and there is no turn to steer. It is not a Runner fault (the pre-change
baseline Runner failed identically) and it was not the CLI version: 1.18.17 and
1.18.31 both fail with the proxy set and both succeed without it. Full
reproduction, the misattribution it caused, and the Runner defect it exposed:
`opencode-acp-blocker.md`.

### ZCode needs a real cancel window

ZCode 0.16.5 accepts `session/cancel` immediately but its turn settles slowly. In
the first attempt (`--cancel-timeout 30`) the cancel was accepted and the turn had
**not** confirmed it stopped at the deadline, so the composite sent nothing and
returned `unknown` / `steer-cancel-unconfirmed` — the correct refusal, since
sending there is exactly how a duplicate dispatch happens. Cancel requested
11:57:48, turn finally settled `cancelled` at ~11:59:31 (~100 s), and it had run
all ten shell steps in the meantime: ZCode's cancel is not a prompt interrupt.
Re-run with `--cancel-timeout 180`: cancel confirmed in ~70 s, then
`interrupted_and_resent` and the steered turn answered `TOPAZ-65-OK`.

## Per-platform findings

### Claude Code — natively supported, bridge gap closed

The ACP bridge as vendored (0.1.0, pin `6c20f28`) advertised no steering and
answered `-32601` on all four entries. That was a **bridge** gap, not a native
one. Claude Code itself injects mid-turn: driving `claude -p --input-format
stream-json --output-format stream-json --verbose` and writing a second `user`
message while the first turn was running produced **one** `result` event with
`num_turns: 3`, and the steer sentinel replaced the remaining tool steps inside
that same turn (`evidence/claude-native-steer-events2.json`: tool `step-1`,
`step-2`, then `STEERED-OK-65`, then the single result).

The vendored bridge now runs every streaming turn over `--input-format
stream-json` with the prompt written to an open stdin, exposes `_session/steering`
through the SDK's `extMethod`, and advertises `_meta.steering.supported`. The
turn still ends on the CLI's own `result` event, which closes stdin so the
per-turn subprocess lifetime is unchanged.

What the CLI does **not** do is acknowledge the steer: there is no reply, no
event, nothing. So the bridge reports `written` with
`steer_confirmation: write-only`, never `injected` — the round-2 correction. It
returns `unknown` instead whenever the write is not known to have landed in a
still-running turn (flush timeout, asynchronous EPIPE, a turn that settled during
the write), and refuses after the CLI's `result`, because a steer written then
starts a NEW turn rather than joining the old one.

Live through the real Runner (`evidence/live-matrix/claude-code-4-steer.json`):
`steer_outcome: written`, `steer_confirmation: write-only`,
`turn_request_id 7 == turn_request_id_after 7`, `turn_request_id_preserved:
true`; the same turn then settled `end_turn` with `"…Step 3 done — printed
step-3.TOPAZ-65-OK"` — the steering instruction was obeyed inside the running
turn, and the codeword from the first prompt proves the context. `stop` clean
with `residual_pids []`.

### Codex — natively supported

`initialize` advertises top-level `_meta.steering: {"supported": true}` and
`_session/steering` is served. The other three entries are `-32601`.

Live through the real Runner (`evidence/live-matrix/codex-4-steer.json`):
`steer_outcome: injected` with `steer_confirmation: agent-confirmed` — the one
channel of the nine that actually confirms consumption — `turn_request_id 7`
preserved across the steer, and the same turn settled `end_turn` with
`"…TOPAZ-65-OK"`, the remaining shell steps abandoned. `stop` clean with
`residual_pids []`.

One semantic fact worth pinning: an **idle** `_session/steering` on Codex 1.11.0
returns `startedNewTurn` even when the request carries
`idleBehavior: "promptRequired"` — it starts a detached turn. The Runner
therefore refuses to steer an idle session before writing anything, and reports
`started_new_turn` distinctly from `injected` if an agent ever does this.

### ZCode — engine-capable, protocol surface does not expose it

The ZCode engine has a real turn-steer queue: the session event enum contains
`turn.steerQueued` and `turn.steerDrained`, a message carries
`steer: {state: notRequested|submitting|steering|guided|fellBack}`, execution
kind `turnSteer` exists, and `steerTurn(...)` is reachable in-process from the
subagent coordinator sink and from tool follow-up input.

It is not reachable over the `app-server --stdio` protocol the Runner drives on
cli 0.16.5:

1. the method table (`rr`) lists no steer method — `session/send` is the only
   input entry;
2. the `session/send` request schema is `.strict()` and has no `delivery`,
   `queueDelivery`, or steer field;
3. `sendPrompt` throws `-32010 "A prompt is already running for this session"`
   whenever `activeAbortController` is set.

Live confirmation (`evidence/idle/zcode.json`): all four entries `-32601`; a
second ordinary `session/prompt` mid-turn did **not** steer — the original turn
ran all twelve steps to completion and the sentinel never appeared.

That live run also exposed a **defect in our own adapter**, now fixed:
`kaola-zcode-acp.py::on_session_prompt` overwrote `session.turn_request_id`, so
the original request (id 10) was orphaned with no response ever and the second
request received the original turn's completion. It now refuses a concurrent
prompt with the same `-32010` ZCode itself uses, and the running turn keeps its
own response attribution. The Runner's holder already refused a second prompt,
so this was only reachable by a client talking to the adapter directly — but it
was a genuine request-attribution bug. Contract test:
`tests/contract/test-zcode-acp-contract.py::test_concurrent_prompt_never_steals_the_active_request_id`.

### Cursor CLI, Devin, Droid, Grok, Kimi CLI, OpenCode

All four candidate entries answer `-32601` and no `initialize` advertises a
steering `_meta`. Grok is explicit about it, returning
`data: "unknown ACP extension method: session/steering"`. Devin advertises a
large `cognition.ai/*` extension set with nothing steering-shaped; Grok
advertises `x.ai/hooks` and `x.ai/capabilities`, likewise.

What a second ordinary prompt does mid-turn on these platforms is recorded in
`evidence/fallback/*.json` (live, one long tool-using turn each). It is a
platform fact, not a Runner capability: the holder refuses a second prompt while
a turn is active, and **none** of these behaviours is a usable steering entry.

| Platform | Original prompt | Second prompt | What actually happened |
|---|---|---|---|
| Cursor CLI | `cancelled` | `end_turn` | the second message **cancels** the original turn and answers in a new one |
| Grok | `end_turn` | `end_turn` | queued to the next turn; the original ran to completion, sentinel never appeared inside it |
| Kimi CLI | `end_turn` | *never settled* | the original completed after 13 tool calls; the second request got no response at all inside the budget |
| Devin | `end_turn` @20.67s | `end_turn` @20.68s | the conversation absorbed the redirection, but **both request ids settle at the same instant** |
| OpenCode | `end_turn` @10.93s | `end_turn` @10.93s | same: absorbed, both requests settle together |
| Droid | `end_turn` @25.24s | `end_turn` @26.02s | second prompt accepted concurrently; both settle, final text unrelated to either instruction |

The Devin / OpenCode / Droid shape is the one that looks like steering, and it is
worth being precise about what was and was not shown. The redirection does reach
the conversation — Devin's own text says *"The user has instructed me to stop the
current process… abandon the loop. STEERED-OK-65"*. What is measured beyond that
is only timing: the two request ids settled 10 ms apart (Devin), in the same
100 ms bucket (OpenCode), and 0.8 s apart (Droid). **Close settlement times are
not proof that attribution was lost** — they are consistent with it, and equally
consistent with two genuinely separate turns finishing back to back. This run did
not establish which, and does not claim to have.

What that shape is *not* is a usable native steering entry: there is no method,
no advertisement, no acknowledgement and no receipt that distinguishes "the
running turn took this" from "a second turn answered it". So none of it is
exposed as native steering. These platforms are steered instead by the explicit
composite, whose attribution is constructed rather than inferred — the cancelled
turn's request id and `cancelled` stop reason are recorded before the new prompt
is sent, and the new turn gets its own id.

## Scope note: PTY and other non-ACP channels

Out of scope for this run by the owner's 2026-09-18 correction. `steer` is an
`acp` operation; over `pty` a mid-turn write is an ordinary keystroke stream, and
whether the native TUI treats it as a steer, a queued next message, or an
interrupt is a per-platform UI behaviour with no receipt that could distinguish
those, so the Runner answers `steer-unsupported-transport` rather than reporting
an unproven injection. `send` remains available and its native effect is the
Agent's to read. Per-platform PTY queue/steer semantics are **not** characterised
here and do not block anything. The earlier exploration of non-ACP channels
(`opencode serve`, `cursor-agent` persistent mode) was stopped under the same
correction; the probe this run had started was killed and no other session was
touched.

## Isolation

Every probe spawned its own agent child in its own scratch cwd, or an exactly
named Runner session this run created and stopped. Nothing touched the
supervising runtime, the pre-existing `vrpcadcore` holders
(`cursor-cli-kaola-vrpcadcore`, `grok-kaola-vrpcadcore`), the tmux session
`kaola-9d0873b0`, or any neighbouring checkout. All Runner sessions this run
created were stopped with `residual_pids []`. The round-3 live matrix and the
round-3 Host acceptance held the same boundary: sessions named `*-kaola-i65m`,
`zcode-kaola-i65host2` and `codex-kaola-i65worker2`, each created and stopped by
this run, plus one owned OpenCode diagnostic session (`opencode-kaola-i65probe`)
that was stopped as soon as it had answered the question. The Host acceptance
installed Skills only into the scratch repo `/private/tmp/kw-i65-e2e2/repo`; no
global install was performed.
