# Finalization summary — Issue #95

Issue: #95 — "ACP worker holder: an exception on the agent reader thread silently kills it and
wedges the session" (P3, single-issue run).
Branch: `workflow/issue-95`. Sink: merge. Accepted candidate:
`14834e835d875f221f60e0be3799c9c997fdfaa8`.

## Delivered

`AgentConnection._read_loop` called `self.holder.on_agent_message(message)` unguarded, so the first
exception escaping a handler ended the reader thread while the agent process stayed alive: every
later `session/update` was dropped, every later JSON-RPC response was never resolved, the turn
stayed `active` forever, and nothing reported it. Issue #92 removed the one trigger then known; the
structure that turned any such exception into a silent, permanent wedge remained.

The reader now scopes a handler failure to the message that caused it and keeps reading. The
failure is recorded as an `agent_message_error` event and counted as `agent_message_errors` in
`status` and in the holder record.

Chosen semantics, stated in the code and unchanged by review:

- An exception is a failure, not a success. The message is **not answered, not retried, and never
  approved** on the agent's behalf; an unanswered agent request stays unanswered and the
  controlling Agent decides from `status`.
- The event carries **locator facts only** — method, JSON-RPC id, exception class, innermost frame.
  The raw message and `str(exc)` are both withheld because either can quote agent payload.
- Recording is **best effort, not a guarantee**: `EventLog.append` already absorbs an `OSError`, so
  an unwritable or full log drops the line. The counter is incremented **before** the call, so
  `status` still reports the failure when the line is what is lost.
- No new thread, restart, watchdog, scheduler, role state, or retry mechanism.

Not attempted, deliberately: no survey of which other handlers on that path can raise (the issue's
`## Hypothesis` says that was never attributed), and no synthesized JSON-RPC reply to the failed
message — `on_agent_request` can already have answered, and a second response to the same id would
be a protocol violation.

## Files Changed

Production: `scripts/kaola-acp-holder.py` (+1 import, +1 counter, the `try/except` boundary,
`note_agent_message_error`, and the counter in `write_record` and `op_state`), propagated by the
renderer into the nine generated `skills/*/scripts/kaola-acp-holder.py` copies.
Tests: new `tests/contract/test-issue-95-reader-exception.py`; `handler_raises` scenario in
`tests/contract/mock-acp-agent.py`; one `handler_errors = 0` line in the hand-initialised
`StubAgent` doubles of `test-issue-65-steer-race.py` and `test-issue-90-event-confirmation-race.py`.
Harness: the suite registered in `scripts/validate.sh` (`python_suites_all` + lane b).
Docs: `CHANGELOG.md`, `docs/runner-v2-dual-transport-design.md` §7.3.

## Test Coverage

`tests/contract/test-issue-95-reader-exception.py`, two tests, driving a real holder through
`kaola-acp.py` against the mock agent's `handler_raises` scenario. The trigger is a **malformed ACP
`session/update`** whose `params` is an array where ACP defines an object; it is one reachable
trigger, and the test docstring says the contract is the boundary on **any** handler path.

- `test_reader_survives_one_failed_message` — the following JSON-RPC response still resolves the
  turn (`turn_completed`/`end_turn`), the following `agent_message_chunk` still reaches
  `final_text`, `status.agent_message_errors >= 1`, the `agent_message_error` event names method /
  `error_type` / frame, no permission event was fabricated, and a planted payload secret is absent
  from the receipt, `status`, `record.json`, and `events.jsonl`.
- `test_exact_stop_settles_without_force` — a non-force `stop` settles under 3.0 s. The baseline
  floor is `CANCEL_GRACE = 5.0`, because a wedged reader can never observe the cancel.

Baseline proof, the final test file run against `git show HEAD:scripts/kaola-acp-holder.py` at the
base commit `e9c427e` — `evidence/01-baseline-FAIL.log`:
`'prompt_timeout' != 'turn_completed'` (empty `final_text`, `mutation_status in_progress`, turn
wedged past the 20 s prompt timeout) and `stop took 5.2s`. Both failures clear with the boundary.

## Validation

verdict: **pass**.
command: `env -u KAOLA_PROJECT_RUNNER_CANONICAL_REPO ./scripts/validate.sh`
result: `EXIT=0`, 34 `OK` blocks, 0 `FAILED (`, 0 `ERROR:`, sweep `residual_pids: []`.
evidence: `evidence/05-validate-post-merge.log` (post-merge re-run on the accepted tree);
`evidence/04-validate-env-unset.log` (same command, pre-merge).
recorded: `.cache/final-validation.md`, `validated_candidate_hash`
`856247528b6c148017b016ceca23abf3656418a2b0d6160ca8a63426002d8ef5`.
finalize `--check`: `validation: chains_green`, `reasons: []`, `dirty_paths: []`.

Honest delta: the recorded run was executed on the accepted tree `14834e8`. Bytes added after it
are documentation and run records only (`docs/runner-v2-dual-transport-design.md`,
`.cache/doc-docking.md`, this summary). No suite reads that design doc — `grep -rn
"runner-v2-dual-transport-design" tests/contract/*.py` returns nothing — and
`render-skills.py --check` was re-run on the docked tree: PASS. The full validate was **not**
repeated, by explicit user instruction.

Round 1 correction, kept on the record rather than smoothed away: round 1's full validate exited 1
on `test-acp-contract.py :: Issue22KimiDefaultYoloAcpTests.test_public_default_start_sets_mode_yolo`
and I attributed it to "pre-existing at HEAD" from a `git archive HEAD` reproduction. That
attribution was wrong in its reasoning: the reproduction inherited the same
`KAOLA_PROJECT_RUNNER_CANONICAL_REPO` from the session environment, so it could only ever reproduce
the same environmental refusal. Worker 94 located the real cause — the suites inherit that variable
and the canonical-root guard then refuses the isolated temp repo. Neither the guard nor the Kimi
test was changed. `evidence/02-validate.log` (the failing first run) and `evidence/03-validate.log`
are kept as-is.

Also mine and fixed, not environmental: round 1's first validate broke
`test-issue-65-steer-race.py` and `test-issue-90-event-confirmation-race.py`, whose
hand-initialised `StubAgent` doubles lacked the new `handler_errors` field that `write_record`
reads. One line each.

## Changed Paths

Reported by the finalize transaction (source-scoped; documentation is not listed):

```
scripts/kaola-acp-holder.py
scripts/validate.sh
skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
tests/contract/mock-acp-agent.py
tests/contract/test-issue-65-steer-race.py
tests/contract/test-issue-90-event-confirmation-race.py
tests/contract/test-issue-95-reader-exception.py
```

## Documentation Docking

`DOCKED` — `.cache/doc-docking.md`. `CHANGELOG.md` and
`docs/runner-v2-dual-transport-design.md` §7.3 fixed; `docs/api.md`, `docs/architecture.md`,
`README.md`, and `docs/acp-watch/*` checked with recorded no-impact reasons; `skills/` and
`hosts/grok-bot/` regenerated, never hand-edited.

## Issue statement coverage

The issue's `## Outcome`: "a worker holder should survive an exception raised while handling an
agent message: the failure should be recorded and the session left observable and stoppable ...
No new scheduler, transport gate, or restart mechanism."

- survives — `test_reader_survives_one_failed_message`, parts 1 and 2.
- recorded — the `agent_message_error` event and the `agent_message_errors` counter, part 3, plus
  the live sample.
- observable — the counter is in `status` and in `record.json`.
- stoppable — `test_exact_stop_settles_without_force`.
- no scheduler / transport gate / restart — the diff adds one `try/except`, one counter, and one
  recorder; nothing else.

The issue's `## Proposed remedy (non-binding)` — guard the call, record in the event log, reflect
in `status` — is what was built.

## Follow-Up Items

None filed. No run-discovered defect remained unaddressed: the two suite breakages were mine and
were fixed inside this run, and the validate-environment finding belongs to worker 94's run, which
diagnosed it and has already sunk. The issue's open `## Hypothesis` — whether other handlers on
that path can raise — is not a defect and stays unattributed; the boundary makes any such case
observable rather than silent, which is the outcome the issue asked for.

## Readiness

READY. Accepted by the outer review at `14834e8` after reading the production diff,
`05-validate-post-merge.log` (EXIT 0, both targeted tests passing, `residual_pids: []`), a clean
worktree, and byte-identical claim records.
