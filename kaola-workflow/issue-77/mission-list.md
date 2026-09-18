# Issue #77: the Issue #73 contract suite must leave no ACP holder behind on a standalone run

Baseline: main `249fc20a80955d1470445c5cbe27eb3c8f8739c1`, worktree
`.kw/worktrees/issue-77`, branch `workflow/issue-77`.

Scope guard: this run owns `tests/contract/test-issue-73-canonical-root.py` and the minimal
evidence Issue #77 requires. It owns no production module and no other session's files
(issues #69, #74, #75, #76 are claimed elsewhere).

Acceptance: running that suite standalone (outside `scripts/validate.sh`, so with no
`TMPDIR` sweep) leaves zero surviving `kaola-acp-holder.py` processes, while
`test_standalone_acp_start_in_a_child_worktree_is_not_refused` still proves the
canonical-root guard does not refuse a standalone ACP start in a child worktree. No assertion
is weakened and no new cleanup framework is introduced.

## 1. Confirm the actual leak mechanism at the frozen baseline
- item: Reproduce the leak the issue reports — run the suite standalone at `249fc20`, capture
  the before `ps` evidence for surviving `kaola-acp-holder.py` processes, and establish which
  test cases actually create a holder (the issue names one; confirm whether the sibling ACP
  cases with `KAOLA_ACP_COMMAND=/bin/false` do too). Read `kaola-acp.py` / the holder to
  establish why the holder outlives `/bin/false` and why the graceful stop returned
  `holder-closed`.
- status: done
- dispatched: self (inline); before-evidence in
  `kaola-workflow/issue-77/evidence/before-standalone-ps.txt`
- result: Reproduced at `249fc20`. `TMPDIR=/tmp/kaola-i77-before python3
  tests/contract/test-issue-73-canonical-root.py` -> 29 tests OK, and exactly ONE residual
  holder, pid 82479, session `i73-test-standalone-acp-start-in-a-child-worktree-is-not-refused`,
  `--command /bin/false`. No other case in the suite leaked: the sibling
  `TestBoundRootReachesTheWorkerRecord` cleanup already reaps its own holder, and the other ACP
  cases are either refused before spawn or never reach `start`.
  Mechanism: a holder does not exit when its agent is gone -- it stays up so that outcome stays
  readable (`scripts/kaola-acp-holder.py:1531` `on_agent_exit` does this for an agent that really
  ran and exited). On THIS host the fixture's `KAOLA_ACP_COMMAND=/bin/false` does not exist
  (macOS ships `/usr/bin/false`), so the spawn fails and the observed holder state is `error`
  /`acp-spawn-failed`, not `agent_exited`. Either way the holder stays alive and only the test
  can reap it. (Corrected after review; the first draft of the comment and commit message named
  `agent_exited` for this host, which is one state off. Behavior and fix are unaffected.)
  The issue's `holder-closed` observation is explained by `op_stop`
  (`scripts/kaola-acp-holder.py:2789`) calling `write_record()`: after `tearDownClass` removes the
  suite tmpdir that write fails and the holder drops the connection, so a post-hoc sweep can only
  force-kill. A stop registered as test cleanup runs BEFORE `tearDownClass`, while the record still
  exists, so it can stop the holder the ordinary way.
  Leaked pid 82479 was swept precisely via `kaola-acp-sweep.py --root /tmp/kaola-i77-before`
  (`matched_pids:[82479], residual_pids:[]`).

## 2. Land the minimal fix and prove before/after
- item: Choose and implement the smallest repair that satisfies acceptance — the issue's two
  non-binding options are an `addCleanup` force-stop for the leaking case, or asserting guard
  passage without starting a holder. Preserve the original before evidence, then re-run the
  suite standalone and capture the after `ps` evidence showing no residual holder. Run
  `./scripts/render-skills.py --check` and `./scripts/validate.sh`.
- status: done
- dispatched: self (inline); candidate in `tests/contract/test-issue-73-canonical-root.py`,
  after-evidence in `kaola-workflow/issue-77/evidence/after-standalone-ps.txt`
- result: Chose the `addCleanup` force-stop (the issue's first option). The second option --
  asserting guard passage on a non-starting command -- was rejected: this is the only case in the
  class that proves a standalone ACP *start* passes the guard, and the non-start form is already
  covered by `test_legacy_acp_session_can_still_be_captured`, so it would have weakened the
  assertion. The assertion itself is untouched; +10 lines, no production file, no new framework.
  The cleanup is registered BEFORE the start (the sibling registers after its first failure point),
  so a start that raises or times out is still reaped.
  A/B on the identical single test, run alone, outside validate.sh:
    baseline     -> 1 residual holder, pid 88971 (`before-single-test-ps.txt`)
    with the fix -> 0 residual holders
  Full suite alone with the fix: 29 tests OK, 0 residual (`after-standalone-ps.txt`).
  `./scripts/render-skills.py --check` -> PASS. `./scripts/validate.sh` -> exit 0 (`evidence/validate.log`);
  it runs this suite in lane B (29 tests, OK) and its own sweep reports `residual_pids: []`.

## 3. Independent review of the frozen candidate
- item: Freeze the candidate commit and have a clean context review it for assertion weakening,
  cleanup ordering (a cleanup registered after a failing assertion never runs), residual-process
  proof, and whether the fix holds when the test fails as well as when it passes. Verdict is
  the orchestrator's.
- status: done
- dispatched: code-reviewer subagent `i77-review`, clean context, on frozen
  `28a1f0872374bc8d19d57e42303b14c5c65637c5`; handback returns to this file as `result`.
  Brief pins the 5 review questions, forbids editing tracked files, forbids touching any
  process or sweep root it did not create (other sessions hold live holders on this machine),
  and excludes the sibling's late-registration ordering from scope.
- result: Verdict ACCEPTED by the orchestrator after reading the handback against the diff.
  Q1 assertion meaning OK (change is additive, +10/-0; `assert_passed_guard` on the START receipt
  is untouched and the cleanup runs after the body). Q2 ordering OK -- reviewer empirically
  confirmed on this host's Python 3.14.3 that addCleanup runs after tearDown and before
  tearDownClass on success, on `self.fail()`, and on a body exception, so register-before-start is
  strictly safer. Q3 reaping verified LIVE, not by timing luck: traced start receipt
  `{"error":{"code":"acp-spawn-failed"},"holder_pid":15294}` then cleanup receipt
  `{"stopped":true,"residual_pids":[]}` and pid 15294 gone; the socket is a digest of
  record_root/platform/session/sha256(repo) so the stop provably targets the holder the start made,
  and `bound=None` cannot be refused because the guard only engages on a non-empty binding. Q4 no
  interference (session name is per-test, record_root per-class). Q5 CONCERN accepted as a known
  limitation, not repaired here: the cleanup discards its receipt, so a FUTURE regression in stop
  could re-leak while the suite stays green. Not repaired because asserting inside cleanup would
  make this guard test fail for stop-side reasons it does not own -- `TestStopInstanceProtection`
  owns stop correctness -- and because it matches the sibling's existing shape. Flagged to the
  outer layer rather than decided unilaterally.
  ONE REVIEWER CORRECTION ACCEPTED AND APPLIED: `/bin/false` does not exist on macOS
  (verified: `ls /bin/false` -> No such file; macOS ships `/usr/bin/false`), so the holder settles
  in `error`/`acp-spawn-failed`, NOT `agent_exited` as my first comment and commit message said.
  Mechanism restated accurately in the comment and commit message; the executable change is
  byte-identical. Reviewer created exactly one holder (pid 15294), reaped by the candidate's own
  cleanup, and touched no foreign process.
