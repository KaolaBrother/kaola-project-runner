# Finalization summary - Issue #77

## Delivered

`tests/contract/test-issue-73-canonical-root.py::TestPreservedBehavior::test_standalone_acp_start_in_a_child_worktree_is_not_refused`
performed a real ACP `start` and never stopped the holder it created, leaking one
`kaola-acp-holder.py` process per standalone run of the suite. It now registers an
`addCleanup` force-stop, so the suite leaves no holder behind while still proving the
canonical-root guard does not refuse a standalone ACP start in a child worktree.

The cleanup is registered **before** the start, so a start that raises or times out is still
reaped, and so it runs before `tearDownClass` deletes the tree - which matters because
`op_stop` rewrites the record, and once that record is gone the holder drops the connection
and only a force kill can reach it.

## Files Changed

- `tests/contract/test-issue-73-canonical-root.py` (+12/-0) - the only tracked source file.

No production module, script, or generated surface was touched.

## Test Coverage

The changed test is itself the coverage. Its assertion is unchanged - `assert_passed_guard`
on the start receipt - so the guarantee Issue #73 established is preserved verbatim.

A/B on the identical single test, run alone outside `validate.sh`:

- main without this change: 1 residual holder (pid 88971)
- with this change: 0 residual holders

## Validation

verdict: pass

- `./scripts/render-skills.py --check` -> PASS (9 workers + orchestrator + grok-bot bridge, budgets OK)
- `./scripts/validate.sh` -> exit 0 at the rebased candidate, zero `FAILED`/`ERROR` lines,
  including the new `PASS: issue-76 permission wake contract (5 tests)`
- `TMPDIR=<fresh> python3 tests/contract/test-issue-73-canonical-root.py` -> `Ran 29 tests ... OK`,
  0 residual holders

Recorded in `.cache/final-validation.md` (`verdict: pass`, `validated_candidate_hash`
`7c11e85eae8b36914230bf3038f27fac654aa6c420bfa81384fc693e0b2ffb2d`).

### Re-verification after syncing onto main 5239fec

Main advanced from `249fc20` to `5239fec` (Issue #76) between acceptance and finalize, touching
`scripts/kaola-acp-holder.py` and `scripts/validate.sh`, so re-verification was load-bearing rather
than ceremonial. The branch was rebased onto `5239fec`; the accepted change is byte-identical
across the rebase.

Re-verification surfaced an intermittent failure: two `subprocess.TimeoutExpired` errors in
`TestBindingRefusesDrift`, only at system load 6.71+. Established as **not caused by this change**
and filed as #78:

- Interleaved A/B, alternating legs on the same machine at load ~3.8-5.2: candidate 4/4 OK,
  main-without-this-change 4/4 OK; 8 further baseline-only runs also passed.
- Structural proof: `TestBindingRefusesDrift` is byte-identical between the two legs and executes
  2nd, while the only class this change touches (`TestPreservedBehavior`) executes 5th.
- One of the two failing cases is PTY transport, which never creates a holder at all.

## Changed Paths

Filled by the finalize transaction.

## Documentation Docking

`DOCKED` - see `.cache/doc-docking.md`. Test-only change; no public behavior, API, setup,
architecture, or validation-policy surface moved. CHANGELOG deliberately not updated.

## Acceptance Legs

- automated: `render-skills.py --check`, `validate.sh`, and the standalone suite - all pass, above.
- local: A/B residual-holder measurement, before/after evidence preserved under `evidence/`.
- independent review: `code-reviewer` in a clean context on the frozen candidate - no defect
  introduced; verified the reap live (start `holder_pid 15294` -> cleanup
  `{"stopped":true,"residual_pids":[]}` -> pid gone). Its one correction (the `/bin/false`
  state error) was applied.
- manual/UAT: none required; no user-facing behavior changed. Nothing left unexecuted.

## Follow-Up Items

- **#78** (P3, filed this run): the #73 suite hits the 60 s `run_cli` timeout under machine load,
  failing two refusal cases. Confirmed independent of this change.
- **Known limitation, accepted, not repaired:** the cleanup discards its stop receipt, so a future
  regression in `stop` could re-leak with the suite still green. Not repaired here because
  asserting inside cleanup would make a canonical-root guard test fail for stop-side reasons it
  does not own - `TestStopInstanceProtection` owns stop correctness.
- **Out of scope, unrepaired:** sibling `TestBoundRootReachesTheWorkerRecord` registers its
  `addCleanup` after a potential `self.fail()` in `receipt()`, so the same leak class is latent on
  its JSON-parse failure path. Never observed leaking; deliberately not touched.

## Correction posted to the issue

Issue #77's stated mechanism ("the holder survives its agent exiting") was corrected before close:
`/bin/false` does not exist on macOS, so the agent is never spawned and the holder settles in
`error`/`acp-spawn-failed`, not `agent_exited`. Posted as a comment on #77.

## Readiness

READY - accepted by the outer layer at `407aa34`, re-verified after the rebase onto `5239fec`.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-77/.cache/doc-docking.md
- kaola-workflow/archive/issue-77/.cache/final-validation.md
- kaola-workflow/archive/issue-77/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-77/evidence/after-standalone-ps.txt
- kaola-workflow/archive/issue-77/evidence/before-single-test-ps.txt
- kaola-workflow/archive/issue-77/evidence/before-standalone-ps.txt
- kaola-workflow/archive/issue-77/evidence/flake-ab-measurement.txt
- kaola-workflow/archive/issue-77/evidence/pre-existing-holders.txt
- kaola-workflow/archive/issue-77/finalization-summary.md
- kaola-workflow/archive/issue-77/mission-list.md
- kaola-workflow/archive/issue-77/workflow-state.md
