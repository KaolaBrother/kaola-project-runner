# Finalization Summary — issue-174

Issue: #174 — `test-issue-98-dsh-acp.py::test_a_confined_boot_write_failure_names_its_cause`
flakes under load: the receipt observes `acp-initialize-timeout` (once the state
`agent_exited`) instead of the expected confined-boot failure code naming its cause.
Branch: `workflow/issue-174` (base `0c3d200`, candidate `dbc6f21`).
Sink: merge.

## Delivered

Root-caused the flake to three observation-ordering races between the agent's
fast boot death and the receipt that must report it, and fixed all three by
ordering, not retrying, in `scripts/kaola-acp-holder.py`:

1. **The failed-frame-write slot was lost.** `send_request` popped the request
   slot from `pending_out` when the frame write failed (the agent already dying
   at the send — the load-dominant path), and `on_agent_exit` cleared
   `pending_out` while resolving the still-pending slots, so `wait_response`'s
   slot lookup missed and returned `None` instantly — which `initialize_agent`
   classified as `acp-initialize-timeout` for a death the holder had already
   observed. (Evidence the wait was never slow: the whole 37-test suite,
   failure included, ran in 4.2 s; the flaky receipt returned instantly.)
   Now a failed request-frame write is remembered on the connection
   (`stdin_write_failed`) and `initialize_agent` classifies a silent wait that
   follows one as `acp-initialize-failed` (write failed); `on_agent_exit`
   resolves the still-pending slots in place (each slot is popped by its own
   single waiter; the reader thread is gone with the agent, so nothing
   re-resolves them) instead of clearing the dict.
2. **The exit published or clobbered the boot verdict.** `on_agent_exit` set
   `state = "agent_exited"` both before `run()` published the real verdict
   (which a start's terminal-state wait breaks on, yielding the once-observed
   `state: agent_exited` / `start-incomplete` receipt) and after it (clobbering
   the published `error`). Now an exit during the boot never touches the
   verdict states: while `state` is `"starting"` the boot's own verdict is
   pending, and a published `"error"` verdict is final; post-boot exits still
   become `"agent_exited"` exactly as before.
3. **The stderr tail was read before the exit was observed.**
   `start_failure_facts` joined the stderr pump only when `exited` was already
   set (a write that broke on the agent's mid-exit stdin close reaches it with
   `exited` still unset, so no drain wait at all) and then only for 1.0 s, so
   under load the EPERM traceback could be undrained and the receipt's
   `stderr_tail` empty. Now the ring is read only after the exit is observed:
   the exit observation is awaited under `EXIT_GRACE` (the codebase's existing
   grace an agent gets to exit after its stdin closes) when a request write
   failed, and the drain join uses the same grace.

No retry, harness, waiting layer, or timing knob was added; the test is
unchanged and not skipped; the mock-agent admission contract
(`pending_out` membership as "the frame was written", pinned by
`test-issue-65-steer-race.py` and `test-issue-90-event-confirmation-race.py`)
is unchanged — an earlier design briefly changed that signal and a concurrent
full validate caught it immediately, driving the final shape.

Independent review: Claude Code review `VERDICT: PASS for issue #174` — each
of the three races verified removed by ordering (not retrying), rendered
copies byte-identical, test unchanged and not skipped, 8/8 green under
concurrent validate with base failing 12/12 in a /tmp clone.

## Files Changed

12 paths, +531/−55 total; excluding the 10 rendered copies +71/−5:

- `scripts/kaola-acp-holder.py` (+46/−5, four sites: the connection fact,
  `send_request`'s write-failure branch, `initialize_agent`'s classification,
  `on_agent_exit`'s verdict-state and in-place resolution,
  `start_failure_facts`' ordered drain)
- `skills/*/scripts/kaola-acp-holder.py` × 10 (re-rendered, byte-identical to
  source via `./scripts/render-skills.py --write` + `--check`, PASS)
- `CHANGELOG.md` (+25, the #174 Unreleased entry)

No frozen surface (`templates/grok-golden/`, `hosts/`), no adapter, bridge, or
`platforms/` file changed. The operator test
`git diff 0c3d200 dbc6f21 -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/adapters platforms`
is non-empty (`scripts/kaola-acp-holder.py` changed), so the entry's
`Seats: restart required` line is accurate.

## Test Coverage

- Focused determinism loop: **20/20 consecutive green** full-suite runs of
  `python3 tests/contract/test-issue-98-dsh-acp.py`, every one while a full
  `./scripts/validate.sh` ran concurrently (`validate_alive=yes` on all 20;
  `/tmp/kpr-i174-loop.log`). Base behavior was 1–4/8 isolated and ~3/3 under
  concurrent validate (dsh #169 / droid #170 / claude #168 receipts).
- Full `./scripts/validate.sh` green three times on the candidate: under the
  concurrent loop load (`/tmp/kpr-i174-validate.log`, exit 0), at rest on the
  final tree (`/tmp/kpr-i174-validate-final.log`, exit 0, zero `FAILED`
  lines), and at finalize time (`/tmp/kpr-i174-validate-finalize.log`, exit
  0, zero `FAILED` lines). The separate known
  `test-issue-65-host-contract.py` cursor-anchor flake did **not** appear in
  any of them, so no exception record is owed.
- Unchanged-suites guard: `test-issue-65-steer-race.py`,
  `test-issue-90-event-confirmation-race.py` (the mock-admission contract),
  `test-issue-146-session-new-wait.py` (late-answer orphaning),
  `test-issue-130-pty-retired.py`, `test-issue-162-upgrade-safety.py`,
  `test-issue-49-grok-bot-host.py` all green.
- No new test was added: the issue's acceptance is determinism of the existing
  test, which is unchanged and not skipped.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py

## Documentation Docking

`.cache/doc-docking.md` — **DOCKED**. `CHANGELOG.md` carries the #174 Unreleased
entry stating **`Seats: restart required.`**, verified against the non-empty
operator-test diff myself (the holder changed, which is the restart-required
set per `docs/conventions.md` and the AGENTS.md release rule). No public API,
command, state vocabulary, or architecture surface changed (the same receipt
codes and fields are produced, deterministically now; all six documented holder
states remain), so no other doc needed an update; the dated PoC/live-verification
docs are historical evidence and are not rewritten.

## Follow-Up Items

- None filed by this run. No run-discovered product defect outside #174's own
  races: the mid-validation discovery that mock suites pin `pending_out`
  membership as the prompt-admission signal was a constraint of the fix's
  design (respected in the final shape), not a product defect; and the
  ambient-`KAOLA_ACP_HEARTBEAT_HOST` fixture-starts refusal seen when invoking
  suites directly outside `validate.sh` is the documented `heartbeat-host-conflict`
  behavior that `validate.sh` itself already neutralizes by dropping the
  inherited `KAOLA_*` namespace (its own comment, `scripts/validate.sh:57-65`).
- The known separate `test-issue-65-host-contract.py` cursor-anchor flake
  (outside this run's scope per the owner briefing) did not appear in any of
  the three green full validates on this candidate; nothing to record.

## Readiness

Acceptance: Claude Code review `VERDICT: PASS for issue #174` (each of the
three races verified removed by ordering, rendered copies byte-identical, test
unchanged and not skipped, 8/8 green under concurrent validate with base
failing 12/12 in a /tmp clone). Candidate frozen at `dbc6f21`, worktree clean.
Final validation recorded: `verdict: pass`, command `./scripts/validate.sh`
(exit 0, zero `FAILED` lines), bound to candidate tree hash
`9e576a345b05606066efb0608843633eba117b47e4259db72b92afafe63f12fd`
(`.cache/final-validation.md`). Ready to archive, sink-merge `workflow/issue-174`
to main (no PR, no release/tag/pin), and close #174 referencing the review PASS.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-174/.cache/doc-docking.md
- kaola-workflow/archive/issue-174/.cache/final-validation.md
- kaola-workflow/archive/issue-174/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-174/finalization-summary.md
- kaola-workflow/archive/issue-174/mission-ledger.jsonl
- kaola-workflow/archive/issue-174/workflow-state.md
