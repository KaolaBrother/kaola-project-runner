# Issue #65 — Finalization summary

Candidate: `57fc091544316b8b42928ca6ba11b30d13d3b72e` on `workflow/issue-65`
(integration merge `bc720e3` of `main` 039c278 + one docs-index commit).
Baseline `bb6d74022bd187e86307a00b93ea8c869caf078f`. Sink: merge. Issue: #65.

## Delivered

**Every ACP platform can be steered mid-run, and the receipt says exactly how.**
A `steer` operation joins `send`/`wait`/`cancel`/`stop` on the same exact
session/repo routing - no scheduler, no second stdin writer, no second
lifecycle - scoped to the ACP channel (`pty` answers
`steer-unsupported-transport`). The Agent picks the mode: `--steer-mode native`
where the platform's own mid-turn entry exists (**Claude Code**, **Codex**), and
`--steer-mode interrupt` everywhere else, which cancels the running turn,
confirms it stopped, and sends the text once as the next prompt on the same ACP
session. With no mode, a platform without a native entry refuses
(`steer-mode-required`) rather than interrupting on its own.

**The receipt never overstates consumption.** `steer_outcome`, `steer_consumed`
and `steer_confirmation` keep `injected` (agent-acknowledged), `written`
(flushed into a turn that acknowledges nothing), `interrupted_and_resent`,
`resent_without_interrupt`, `started_new_turn`, `not_consumed`, `unsupported`,
`rejected` and `unknown` apart. The composite is interrupted-then-continued with
`side_effects_possible`, never injection.

**Turn attribution is bound to the turn object.** `cancel` takes an
`expected_request_id`; the composite passes the turn it snapshotted, and the
admission check, outbound `session/cancel`, wait and receipt are all taken from
that one turn under the lock. A turn replaced in between is never cancelled,
never impersonated and never blind-resent (`steer-turn-changed`); `cancel_sent`
separates "cancelled nothing" from "asked it to stop, outcome unconfirmed"; a
turn that ended on its own is `resent_without_interrupt`, not a claimed
interruption; a dispatched turn's id comes from its own admission; and a late
answer can no longer settle the turn running now.

**The ZCode Host post-dispatch contract is operating instructions.** The main
Skill states the action rules (identity bootstrap, `KAOLA_ACP_HEARTBEAT_HOST` per
worker `start` with its receipt check, `send --no-wait` read as accepted-not-done
with `dispatch_event_cursor` kept as the reading anchor, update the one
`.kaola/heartbeat-prompt.json`, then end the turn - that is the wait), and a Host
awaiting in-flight workers is explicitly not a stoppable idle worker. Two new
on-demand references carry the detail without duplicating each other:
`references/zcode-host-dispatch.md` (the beat, the event shape, the carrier) and,
from Issue #66, `references/host-startup.md` (entry points, startup, receipt).

Two real defects found and fixed on the way: `kaola-zcode-acp.py` overwrote the
active turn's request id when a second prompt arrived (now refused with
`-32010`), and a holder whose `start` never negotiated an ACP session id answered
`in_progress`/`steer_consumed: true` for text nothing received (now
`no-acp-session`, nothing written).

## Files Changed

148 files, +13052/-705 from baseline `bb6d740`; 113 files, +10758/-560 against
`main` at the merge. Sources: `scripts/kaola-acp-holder.py`, `kaola-acp.py`,
`kaola-tmux.sh`, `kaola-zcode-acp.py`, `render-skills.py`, `validate.sh`;
`platforms/*.yaml` (three new keys on all nine); `templates/SKILL.md.tmpl`,
`templates/references/{acp,steering}.md.tmpl`,
`templates/orchestrator/{SKILL.md.tmpl,references/*}`;
`vendor/claude-code-acp/src/{claude-runner,agent}.ts` and its rebuilt `dist/`;
docs (`api.md`, `zcode-host.md`, `README.md`, `docs/README.md`, `CHANGELOG.md`).
`skills/` and `hosts/grok-bot/` are renderer output only;
`templates/grok-golden/` untouched.

## Test Coverage

- `tests/contract/test-issue-65-steering.py` — 27 tests: manifest capability
  pairing across all nine platforms, mode-required refusal, native and composite
  paths, idle refusal, turn-end race, consecutive steers, cancel interaction,
  unknown mapping, session isolation, null-session refusal, and "every platform
  has a documented usable path".
- `tests/contract/test-issue-65-steer-race.py` — 7 tests, in-process against the
  real `Holder` with a stubbed agent, arranging each interleaving directly
  (0.02 s, no sleeps, no production hook).
- `tests/contract/test-issue-65-host-contract.py` — 13 tests pinning the Host
  wording, the reference's runnable elements, and a behavioural proof that the
  turn-end cursor loses the reply while `dispatch_event_cursor` keeps it.
- `vendor/claude-code-acp/tests/kaola-steer.test.ts` — 10 tests: prompt on stdin
  not argv, `written` never `injected`, backpressure, async flush error →
  `unknown`, settle-during-write, post-`result` refusal, flush timeout.
- `test-zcode-acp-contract.py` gained the concurrent-prompt attribution test.
  Both new suites are wired into `scripts/validate.sh`'s two lanes.

## Validation

- `./scripts/validate.sh` — **exit 0**, every contract suite green, at
  `57fc091`. Log: `evidence/validate/validate-final-57fc091.txt` (the repository
  ignores `*.log`, so the raw run logs are archived as `.txt`); the integration
  and pre-integration runs are kept beside it.
- `./scripts/render-skills.py --check` — PASS, `budgets OK`, no budget raised
  (`templates/budgets.json` untouched; main Skill 17262 B of 17408).
- `vendor/claude-code-acp/kaola-dist.py --check` — OK, 12 inputs, rebuild
  byte-identical.
- Recorded receipt: `.cache/final-validation.md`, `verdict: pass`,
  command `./scripts/validate.sh`.
- **Live, nine of nine platforms**, through the generated Skill's own script,
  each run planting the codeword `TOPAZ-65` in the first prompt and requiring it
  back after the steer (`evidence/live-matrix/`): codex `injected`;
  claude-code `written` with the steer obeyed inside the same turn; cursor-cli,
  devin, droid, grok, kimi-cli, opencode and zcode `interrupted_and_resent`.
  Every session stopped with `residual_pids []`.
- **Live ZCode Host acceptance, twice** (`evidence/live-host-acceptance.md`,
  `evidence/live-host2-acceptance.md`): a real ZCode Host 0.16.5, from the
  generated Skill alone, bound the carrier, dispatched `--no-wait`, ended its
  turn, was woken by the worker event, read the reply **from the dispatch
  anchor** and verified it, then closed out.

## Changed Paths

Reported by the finalize transaction (108 paths, `dirty_paths: []`):

- `platforms/` — 9 file(s): `platforms/claude-code.yaml`, `platforms/codex.yaml`, `platforms/cursor-cli.yaml`, `platforms/devin.yaml`, `platforms/droid.yaml`, `platforms/grok.yaml`, …
- `scripts/` — 6 file(s): `scripts/kaola-acp-holder.py`, `scripts/kaola-acp.py`, `scripts/kaola-tmux.sh`, `scripts/kaola-zcode-acp.py`, `scripts/render-skills.py`, `scripts/validate.sh`
- `skills/` — 70 generated files across the nine workers and the main Skill (renderer output only)
- `templates/` — 7 file(s): `templates/SKILL.md.tmpl`, `templates/orchestrator/SKILL.md.tmpl`, `templates/orchestrator/references/grok-bot-host.md`, `templates/orchestrator/references/host-startup.md.tmpl`, `templates/orchestrator/references/zcode-host-dispatch.md.tmpl`, `templates/references/acp.md.tmpl`, …
- `tests/` — 10 file(s): `tests/contract/fake-claude.py`, `tests/contract/mock-acp-agent.py`, `tests/contract/test-generated-skills.py`, `tests/contract/test-issue-24-opencode-pty-bypass.py`, `tests/contract/test-issue-50-claude-acp-bridge.py`, `tests/contract/test-issue-50-runner-integration.py`, …
- `vendor/` — 6 file(s): `vendor/claude-code-acp/UPSTREAM.md`, `vendor/claude-code-acp/dist/DERIVATION.json`, `vendor/claude-code-acp/dist/index.js`, `vendor/claude-code-acp/src/agent.ts`, `vendor/claude-code-acp/src/claude-runner.ts`, `vendor/claude-code-acp/tests/kaola-steer.test.ts`

## Documentation Docking

`DOCKED` — `.cache/doc-docking.md` lists every checked file with its fix or its
no-impact reason.

## Acceptance legs

- Automated: `./scripts/validate.sh` (exit 0) plus the per-suite runs above.
- Local live: the nine-platform steering matrix and the two ZCode Host loops,
  on the real installed CLIs with versions recorded in
  `evidence/steering-capability-matrix.md`.
- Manual/UAT: none required by the issue; none claimed.
- External review: the outer Codex supervisor reviewed five candidates
  (`71d6dd2` REQUEST_CHANGES, `cd98e2d`, `b62f957`, `36e6f51`, `fd37a4f`) and
  ACCEPTed `4b8168c` and the integration `bc720e3`.

## Issue acceptance walk

Every acceptance line in #65 is satisfied except one, which is explicitly
partial and filed:

- Nine-platform row-by-row investigation, capability separate from Runner
  status, versioned evidence, no `unknown` left standing — **met**
  (`evidence/steering-capability-matrix.md`).
- A callable tool on every natively supported platform; no tool advertised where
  the entry does not exist — **met**, and the owner's mid-run scope correction
  went further: every platform now has a usable composite path.
- Real long-turn steering absorbed, with the original request id and terminal
  state preserved — **met**, live on codex and claude-code.
- turn-end race, not-consumed, consecutive steers, cancel, disconnect-unknown,
  session isolation, no request-id overwrite, no duplicate send — **met**
  (27 + 7 + 10 tests, several proven RED against the pre-fix code).
- No regression in `send`/`wait`/`cancel`/`stop` or the supported channels —
  **met** (validate exit 0).
- A real ZCode Host loading the Skill itself, non-blocking dispatch, prompt
  update, ending its own turn, session preserved, woken by a worker event with
  no external poke — **met**, twice.
- "covering an ordinary Worker **and an inner ZCode Worker**", multiple workers,
  failure, busy staging, resume redelivery, dedupe — **partially met**. Busy
  staging, turn-boundary delivery, confirmation, dedupe, resume redelivery and
  the nested Host/inner-ZCode isolation with exact stop are covered by contract
  tests, and the live loops used a real Codex worker. A **live** inner-ZCode
  worker and a live multi-worker/failure beat were not exercised. Filed as
  **#69** (P2) with the measurement, the reason it is an evidence gap rather
  than a known defect, and a non-binding remedy.
- Main Skill, generated files and installer payload consistent; `--write`,
  `--check`, `validate.sh` — **met**.
- Live evidence bound to the candidate SHA and real versions; tests cleaning up
  only their own exact resources — **met**; every probe session was stopped with
  `residual_pids []` and the pre-existing `vrpcadcore` sessions, tmux
  `kaola-9d0873b0`, the neighbouring checkouts and the issue-68 run were never
  touched.

## Follow-Up Items

- **#69** (P2) — live inner-ZCode-Worker and multi-worker/failure Host beats.
- PTY/TUI steering semantics remain deliberately out of scope by the owner's
  2026-09-18 correction; `steer` answers `steer-unsupported-transport` there.
- Two evidence-claim corrections made during review are recorded in
  `mission-list.md` (Mission 9, revisions 1 and 2) rather than silently fixed:
  an overstated "5 of 6 RED" count, and a test that claimed a takeover it did
  not exercise.

## Readiness

Ready to sink. `./scripts/validate.sh` exit 0 at the candidate, documentation
docked, one follow-up filed, no unfinished work owned by this run.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-65/.cache/doc-docking.md
- kaola-workflow/archive/issue-65/.cache/final-validation.md
- kaola-workflow/archive/issue-65/.cache/mirror-digest.json
- kaola-workflow/archive/issue-65/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-65/evidence/claude-code.json
- kaola-workflow/archive/issue-65/evidence/claude-native-steer-events.json
- kaola-workflow/archive/issue-65/evidence/claude-native-steer-events2.json
- kaola-workflow/archive/issue-65/evidence/codex.json
- kaola-workflow/archive/issue-65/evidence/cursor-cli.json
- kaola-workflow/archive/issue-65/evidence/devin.json
- kaola-workflow/archive/issue-65/evidence/droid.json
- kaola-workflow/archive/issue-65/evidence/fallback/cursor-cli.json
- kaola-workflow/archive/issue-65/evidence/fallback/cursor-cli.stderr
- kaola-workflow/archive/issue-65/evidence/fallback/devin.json
- kaola-workflow/archive/issue-65/evidence/fallback/devin.stderr
- kaola-workflow/archive/issue-65/evidence/fallback/droid.json
- kaola-workflow/archive/issue-65/evidence/fallback/droid.stderr
- kaola-workflow/archive/issue-65/evidence/fallback/grok.json
- kaola-workflow/archive/issue-65/evidence/fallback/grok.stderr
- kaola-workflow/archive/issue-65/evidence/fallback/kimi-cli.json
- kaola-workflow/archive/issue-65/evidence/fallback/kimi-cli.stderr
- kaola-workflow/archive/issue-65/evidence/fallback/opencode.json
- kaola-workflow/archive/issue-65/evidence/fallback/opencode.stderr
- kaola-workflow/archive/issue-65/evidence/grok.json
- kaola-workflow/archive/issue-65/evidence/idle/claude-code.json
- kaola-workflow/archive/issue-65/evidence/idle/claude-code.stderr
- kaola-workflow/archive/issue-65/evidence/idle/codex.json
- kaola-workflow/archive/issue-65/evidence/idle/codex.stderr
- kaola-workflow/archive/issue-65/evidence/idle/cursor-cli.json
- kaola-workflow/archive/issue-65/evidence/idle/cursor-cli.stderr
- kaola-workflow/archive/issue-65/evidence/idle/devin.json
- kaola-workflow/archive/issue-65/evidence/idle/devin.stderr
- kaola-workflow/archive/issue-65/evidence/idle/droid.json
- kaola-workflow/archive/issue-65/evidence/idle/droid.stderr
- kaola-workflow/archive/issue-65/evidence/idle/grok.json
- kaola-workflow/archive/issue-65/evidence/idle/grok.stderr
- kaola-workflow/archive/issue-65/evidence/idle/kimi-cli.json
- kaola-workflow/archive/issue-65/evidence/idle/kimi-cli.stderr
- kaola-workflow/archive/issue-65/evidence/idle/opencode.json
- kaola-workflow/archive/issue-65/evidence/idle/opencode.stderr
- kaola-workflow/archive/issue-65/evidence/idle/zcode.json
- kaola-workflow/archive/issue-65/evidence/idle/zcode.stderr
- kaola-workflow/archive/issue-65/evidence/kimi-cli.json
- kaola-workflow/archive/issue-65/evidence/live-host-acceptance.md
- kaola-workflow/archive/issue-65/evidence/live-host/1-host-start.json
- kaola-workflow/archive/issue-65/evidence/live-host/2-host-beat1.json
- kaola-workflow/archive/issue-65/evidence/live-host/3-host-observe.json
- kaola-workflow/archive/issue-65/evidence/live-host/4-host-observe2.json
- kaola-workflow/archive/issue-65/evidence/live-host/5-host-beat2.json
- kaola-workflow/archive/issue-65/evidence/live-host/6-host-capture-full.json
- kaola-workflow/archive/issue-65/evidence/live-host/7-host-stop.json
- kaola-workflow/archive/issue-65/evidence/live-host/8-worker-status.json
- kaola-workflow/archive/issue-65/evidence/live-host/host-event-chain.json
- kaola-workflow/archive/issue-65/evidence/live-host2-acceptance.md
- kaola-workflow/archive/issue-65/evidence/live-host2/1-host-start.json
- kaola-workflow/archive/issue-65/evidence/live-host2/2-host-beat1-send.json
- kaola-workflow/archive/issue-65/evidence/live-host2/3-host-observe.json
- kaola-workflow/archive/issue-65/evidence/live-host2/4-host-capture.json
- kaola-workflow/archive/issue-65/evidence/live-host2/5-host-stop.json
- kaola-workflow/archive/issue-65/evidence/live-host2/host-events.jsonl
- kaola-workflow/archive/issue-65/evidence/live-matrix/claude-code-1-start.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/claude-code-2-send.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/claude-code-3-observe.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/claude-code-4-steer.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/claude-code-5-wait.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/claude-code-6-stop.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/codex-1-start.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/codex-2-send.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/codex-3-observe.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/codex-4-steer.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/codex-5-wait.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/codex-6-stop.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/cursor-cli-1-start.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/cursor-cli-2-send.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/cursor-cli-3-observe.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/cursor-cli-4-steer.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/cursor-cli-5-wait.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/cursor-cli-6-stop.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/devin-1-start.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/devin-2-send.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/devin-3-observe.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/devin-4-steer.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/devin-5-wait.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/devin-6-stop.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/droid-1-start.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/droid-2-send.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/droid-3-observe.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/droid-4-steer.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/droid-5-wait.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/droid-6-stop.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/grok-1-start.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/grok-2-send.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/grok-3-observe.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/grok-4-steer.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/grok-5-wait.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/grok-6-stop.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/kimi-cli-1-start.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/kimi-cli-2-send.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/kimi-cli-3-observe.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/kimi-cli-4-steer.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/kimi-cli-5-wait.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/kimi-cli-6-stop.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/opencode-1-start.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/opencode-2-send.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/opencode-3-observe.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/opencode-4-steer.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/opencode-5-wait.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/opencode-6-stop.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/opencode-scratch-start.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/zcode-1-start.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/zcode-2-send.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/zcode-3-observe.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/zcode-4-steer.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/zcode-5-wait.json
- kaola-workflow/archive/issue-65/evidence/live-matrix/zcode-6-stop.json
- kaola-workflow/archive/issue-65/evidence/live/claude-code-1-start.json
- kaola-workflow/archive/issue-65/evidence/live/claude-code-2-send.json
- kaola-workflow/archive/issue-65/evidence/live/claude-code-3-observe.json
- kaola-workflow/archive/issue-65/evidence/live/claude-code-4-steer.json
- kaola-workflow/archive/issue-65/evidence/live/claude-code-5-wait.json
- kaola-workflow/archive/issue-65/evidence/live/claude-code-6-capture.json
- kaola-workflow/archive/issue-65/evidence/live/claude-code-7-stop.json
- kaola-workflow/archive/issue-65/evidence/live/codex-1-start.json
- kaola-workflow/archive/issue-65/evidence/live/codex-2-send.json
- kaola-workflow/archive/issue-65/evidence/live/codex-3-observe.json
- kaola-workflow/archive/issue-65/evidence/live/codex-4-steer.json
- kaola-workflow/archive/issue-65/evidence/live/codex-5-wait.json
- kaola-workflow/archive/issue-65/evidence/live/codex-6-capture.json
- kaola-workflow/archive/issue-65/evidence/live/codex-7-stop.json
- kaola-workflow/archive/issue-65/evidence/opencode-acp-blocker.md
- kaola-workflow/archive/issue-65/evidence/opencode.json
- kaola-workflow/archive/issue-65/evidence/probes/claude_ack_probe.py
- kaola-workflow/archive/issue-65/evidence/probes/live-host-e2e2.sh
- kaola-workflow/archive/issue-65/evidence/probes/live-steer-matrix.sh
- kaola-workflow/archive/issue-65/evidence/probes/live-steer.sh
- kaola-workflow/archive/issue-65/evidence/probes/native_entry_scan.py
- kaola-workflow/archive/issue-65/evidence/probes/run-idle.sh
- kaola-workflow/archive/issue-65/evidence/probes/run-live-fallback.sh
- kaola-workflow/archive/issue-65/evidence/probes/run-live-matrix.sh
- kaola-workflow/archive/issue-65/evidence/probes/steer_probe.py
- kaola-workflow/archive/issue-65/evidence/round2/claude-ack-after_result.json
- kaola-workflow/archive/issue-65/evidence/round2/claude-ack-close_race.json
- kaola-workflow/archive/issue-65/evidence/round2/claude-ack-midturn.json
- kaola-workflow/archive/issue-65/evidence/round2/native-entry-scan.json
- kaola-workflow/archive/issue-65/evidence/steering-capability-matrix.md
- kaola-workflow/archive/issue-65/finalization-summary.md
- kaola-workflow/archive/issue-65/mission-list.md
- kaola-workflow/archive/issue-65/workflow-state.md
