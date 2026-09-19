# Issue #95 — an exception on the ACP holder's agent reader thread must not silently kill it

Run facts: branch `workflow/issue-95`, worktree
`/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-95`,
base `e9c427e`. Scope is this issue only: production diff, a targeted regression test, and the
documentation the change makes untrue. Another worker owns `bundle-94`/Issue #94 — never touch it
or `main`. No finalize/archive/sink/close/push before the outer ACCEPT. No extra implementation or
review subagents this run (user-directed); everything is inline.

Owner note: user requires extreme minimality. No restart, watchdog, scheduler, role state, or retry
mechanism. An exception must not read as success, must never auto-approve, and must not leak the
raw agent message or credentials carried inside an exception's text.

---

## 1. Bounded regression baseline

- item: Write a bounded regression test that drives a real `kaola-acp-holder.py` holder and proves,
  at base `e9c427e`, that a single message whose handling raises kills `AgentConnection._read_loop`
  so a following well-formed `session/update` and a following JSON-RPC response are never processed.
  Keep it a targeted contract suite in `tests/contract/`, in the style of the existing ACP suites.
- status: todo
- dispatched:
- result:

## 2. Minimal exception boundary

- item: Add the smallest boundary around the `self.holder.on_agent_message(message)` call in
  `_read_loop` that keeps the reader alive for subsequent messages, records the failure in the
  holder event log with locator facts only (no raw message, no exception text), and reflects a
  count in the holder record and in `status` so the failure is visible rather than silent. State
  the chosen semantics for the failed message explicitly; do not synthesize an agent reply and do
  not approve anything.
- status: done
- dispatched: self (inline)
- result: `scripts/kaola-acp-holder.py`. `try/except Exception` around the one
  `on_agent_message` call; `AgentConnection.handler_errors` counter; new
  `Holder.note_agent_message_error` appending an `agent_message_error` event; the counter is
  surfaced as `agent_message_errors` in `write_record` and in `op_state` (the `status` payload).
  Chosen semantics, stated in the code: the failure is scoped to that ONE message and the reader
  keeps reading; the message is NOT answered, NOT retried, and NOT approved, so an unanswered
  agent request stays unanswered and the controlling Agent decides from `status`; the event
  carries locator facts only (method, JSON-RPC id, exception class, innermost frame) and withholds
  both the raw message and `str(exc)` because either can quote agent payload. No write_record call
  inside the failure path, so the error path adds no new way to fail. Suite registered in
  `scripts/validate.sh` (`python_suites_all` + lane b). Post-fix: both tests pass in 8.7 s.

## 3. Documentation and render

- item: Update only the documentation the change makes untrue, then run
  `./scripts/render-skills.py --write` and `--check`. `skills/` and `hosts/grok-bot/` are generated;
  never hand-edit.
- status: done
- dispatched: self (inline)
- result: `CHANGELOG.md` Unreleased entry for Issue #95. `docs/api.md` does not enumerate holder
  counters and `docs/architecture.md` does not describe the reader loop's failure semantics, so
  nothing there became untrue. `./scripts/render-skills.py --write` then `--check` => PASS
  (9 workers + kaola-project-runner + kaola-delegator + grok-bot host, budgets OK); the render
  propagated the holder change into the nine `skills/*/scripts/kaola-acp-holder.py` copies.

## 4. Full validate and frozen evidence

- item: Run `./scripts/validate.sh` once in full, freeze the candidate SHA, and assemble the review
  packet for the user: frozen SHA, the real diff, the baseline failure evidence, and the post-fix
  pass evidence. Stop there and await the outer ACCEPT.
- status: done
- dispatched: self (inline)
- result: Frozen candidate `18f7960c008663ea3e2122e888701d4a7cea9f1b` on `workflow/issue-95`
  (16 files, +556/-10). Full `./scripts/validate.sh`:
  `kaola-workflow/issue-95/evidence/03-validate.log`, exit 1 with exactly ONE failing suite,
  `test-acp-contract.py :: Issue22KimiDefaultYoloAcpTests.test_public_default_start_sets_mode_yolo`
  (`FileNotFoundError: .../mock-events.jsonl`). ATTRIBUTION: that failure reproduces identically on
  an untouched `git archive HEAD` tree of the base commit `e9c427e`, so it is pre-existing and not
  Issue #95's; it is reported to the user, not fixed here. The first validate run
  (`02-validate.log`) also failed `test-issue-65-steer-race.py` and
  `test-issue-90-event-confirmation-race.py` — those WERE mine: their hand-initialised `StubAgent`
  doubles lacked the new `handler_errors` field that `write_record` reads. One line added to each
  double; both suites pass in `03-validate.log`. Sweep reports no residual pids. Live sample
  captured: `agent_message_errors = 1`, event
  `{"kind":"agent_message_error","method":"session/update","id":null,"error_type":"AttributeError","at":"kaola-acp-holder.py:1578"}`,
  turn `turn_completed`/`end_turn` with the following chunk delivered.
  Awaiting the outer ACCEPT. No finalize, archive, sink, close, or push.

---

Round 2 (after the outer review of `18f7960`: the exception-boundary direction was judged sound,
but NOT accepted; four closing-evidence items were assigned, with no expansion of the production
design). Round 1 results above are closed and unchanged.

## 5. Correct the framing and the recording claim

- item: The candidate must not claim the failure recording can never fail — `EventLog.append`
  already absorbs `OSError`, so keep the change small and state the real durability. And "legal
  JSON-RPC by-position params" is not the same as a legal ACP `session/update`: describe the
  trigger as a malformed ACP message. No generalized recovery, retry, or state machine.
- status: done
- dispatched: self (inline)
- result: commit `c91d505`. (a) The `note_agent_message_error` docstring now says recording is best
  effort, names `EventLog.append`'s existing `OSError` absorption as the reason, and states why the
  failure is still reported when the LINE is what is lost - the counter is incremented before the
  call. No new guard, try, retry, or state machine; the executable code is unchanged. NOTE for the
  record: round 1's mission 2 result claimed "the error path adds no new way to fail". That was an
  over-claim and is corrected here rather than edited there; the honest statement is the one now in
  the docstring. (b) The trigger is described as a malformed ACP `session/update` (`params` an array
  where ACP defines an object) in the test docstring, the mock scenario comment, and the CHANGELOG;
  the "legal JSON-RPC by-position params" framing is gone, and the test docstring now says the
  contract is the boundary on ANY handler path. Re-rendered: `--check` PASS.

## 6. The real run and its raw evidence, in the candidate branch

- item: The candidate worktree carried no `kaola-workflow/issue-95/mission-list.md`; the real
  claim and run live in the main root. Establish where each file actually is, bring the existing
  run and the necessary raw evidence into the candidate branch as-is, and verify byte identity by
  hash. Do not re-claim and do not rewrite history.
- status: done
- dispatched: self (inline)
- result: ACTUAL LOCATIONS, established before copying. The claim script wrote the run to the MAIN
  ROOT, not the worktree: `/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/`
  `kaola-workflow/issue-95/{workflow-state.md, mission-list.md, .cache/origin/selection-record.json}`.
  The evidence logs were written where I ran them, inside the candidate worktree at
  `.kw/worktrees/issue-95/kaola-workflow/issue-95/evidence/`. Round 1's `git add -A` committed NONE
  of it: `git ls-tree HEAD -- kaola-workflow` was empty, because the run records were in the other
  root and `.gitignore:2 *.log` covered every log (`git check-ignore -v` confirms). Both are now in
  the branch: the three run records copied from the main root, and the five evidence logs added with
  `git add -f`. Byte identity verified by `shasum -a 256` on each pair (see mission 7's result for
  the transcript); `selection-record.json` hashes to `1a86bcf6...`, which is exactly the
  `selection_record_digest` recorded in `workflow-state.md`. The main root keeps its own live copy -
  nothing moved, no re-claim, no history rewrite.

## 7. The exact validate command, main sync, and a new frozen SHA

- item: Worker 94 located round 1's validate failure: the suites inherit
  `KAOLA_PROJECT_RUNNER_CANONICAL_REPO`, so an isolated temp repo is refused by the
  canonical-root guard. It reproduces on the same main, and
  `env -u KAOLA_PROJECT_RUNNER_CANONICAL_REPO ./scripts/validate.sh` passes there. Run that exact
  command once in this worktree and record the actual exit. Do not change the guard and do not
  change the Kimi test; ordinary production Runner commands stay bound to KPR. Then, at a safe
  point, sync the latest main and freeze a new SHA. No finalize, archive, sink, close, or push
  before the outer ACCEPT.
- status: done
- dispatched: self (inline)
- result: 1) EXACT COMMAND, pre-merge:
  `env -u KAOLA_PROJECT_RUNNER_CANONICAL_REPO ./scripts/validate.sh` => `EXIT=0`,
  34 OK blocks, 0 `FAILED (`, 0 `ERROR:`, sweep residual_pids empty.
  `kaola-workflow/issue-95/evidence/04-validate-env-unset.log`. `test-acp-contract.py` (all 46
  tests, including `Issue22KimiDefaultYoloAcpTests.test_public_default_start_sets_mode_yolo`)
  passes. Worker 94's diagnosis is confirmed and it CORRECTS round 1's attribution: the failure was
  never a code failure in either tree. Round 1 concluded "pre-existing at HEAD" from a
  `git archive HEAD` reproduction, but that reproduction inherited the same
  `KAOLA_PROJECT_RUNNER_CANONICAL_REPO` from this session's environment, so it could only ever show
  the same environmental refusal. The guard and the Kimi test are untouched, and ordinary
  production Runner commands stay bound to KPR.
  2) MAIN SYNC. Issue #94 sank while this round ran: `origin/main` moved `e9c427e` -> `a31fdc9`
  (11 commits). Merged with `--no-ff` as `5cb461d`; no conflicts, no rebase, no history rewrite.
  Both #94 and #95 changes coexist in the shared files, verified by reading the merged tree:
  `scripts/kaola-acp-holder.py` holds `HOST_SKILL_ENTRY` (#94, line 174) AND `handler_errors`
  (line 593) plus `note_agent_message_error` (line 1499); `scripts/validate.sh` lists both
  `test-issue-94-zcode-native-skill-entry.py` and `test-issue-95-reader-exception.py` in
  `python_suites_all` and in lane b. `render-skills.py --check` PASS.
  3) POST-MERGE RE-VALIDATE, because the merge changed bytes that round 1's PASS covered. Same
  exact command => `EXIT=0`, 34 OK, 0 `FAILED (`, 0 `ERROR:`, sweep clean; the Issue #95 suite
  passes in 1.93 s. `kaola-workflow/issue-95/evidence/05-validate-post-merge.log`.
  4) Frozen: see the final SHA reported to the user. No finalize, archive, sink, close, or push.
