# What the already-archived Issue #77 evidence proves on its own (no new runs)

Sources, both already tracked in the repo at base f6be8a3:
- `kaola-workflow/archive/issue-77/evidence/flake-failing-run.log`
- the Issue #78 follow-up comment's `ps` listing of the four orphans

## 1. The machine was NOT globally slow. Only those two invocations stopped.

`Ran 29 tests in 145.317s`. The normal suite is ~24 s. Two timeouts at 60 s each = 120 s.
24 + 120 = 144 s, against 145.317 s measured. The other 27 tests therefore ran at
essentially their normal aggregate cost during the very same loaded run.

Consequence: load-driven arithmetic slowdown is refuted as the mechanism. Whatever
happened was a block confined to two invocations, not a slowdown spread across the suite.
This also independently refutes the issue's own stated hypothesis ("the refusal path may
simply be spending that long in process and `git` startup before the guard is reached") -
process and git startup were demonstrably cheap for the other 27 cases in that run.

## 2. The orphans hung from their first moment, not near the end.

From the follow-up comment's `ps` lstart column:

    run 1:  grok  21:29:10   ->  codex 21:30:10    (exactly 60 s apart)
    run 2:  grok  21:32:47   ->  codex 21:33:47    (exactly 60 s apart)

The second case in each run starts exactly when the first case's 60 s timeout expires.
So each invocation blocked essentially at spawn and consumed the whole budget; neither
made partial progress and stalled late. A raised timeout would therefore not have
completed them - it would only have lengthened the run, exactly as the comment argues.

## 3. The two leads are perfectly confounded in this run, and must be split by a new leg.

Method order within `TestBindingRefusesDrift` is alphabetical, and the log confirms it:

    1 test_acp_transport_is_refused_by_the_same_shared_guard   grok  acp  child_a  ERROR
    2 test_child_worktree_of_the_same_repository_is_refused    codex pty  child_a  ERROR
    3 test_refusal_happens_before_the_acp_agent_is_launched    grok  acp  child_b  ok
    4 test_second_child_worktree_is_refused_too                codex pty  child_b  ok
    5 test_unrelated_repository_is_refused                     codex pty  other    ok

Read by target, it is a clean factorial and `child_a` is the discriminator: the same
grok/acp pair passes on child_b (case 3) and the same codex/pty pair passes on child_b
and on the unrelated repo (cases 4, 5). Read by position, "the first two invocations of
the class" fits the identical data.

The two cannot be separated from this run, because child_a happens to occupy positions
1 and 2. Mission 1 must run the discriminating leg: child_b in position 1-2, and child_a
in a later position.

## 4. What the refusal path actually does with `--repo`, measured at base f6be8a3

A full traced refusal spans 65 ms end to end. Everything the guard does with the
requested `--repo` is `canonical_dir "$repo"`, i.e. `(cd "$repo" 2>/dev/null && pwd -P)`,
then a string comparison, then `emit_json` and `exit 1`. The only subprocesses on the
whole path are two `python3` spawns (manifest read at kaola-tmux.sh:128, `emit_json` at
kaola-tmux.sh:41) plus one `git rev-parse --show-toplevel` against the *bound* root,
which is identical for all five drift cases and so cannot by itself explain a split
between them.

## 5. Storage is not the explanation

`/Volumes/WorkspaceA` is a local PCI-Express APFS volume (`/dev/disk7s2`, `apfs, local,
nodev, nosuid, journaled, noowners`), not a network or disk-image mount. A 60 s I/O stall
there is implausible, and in any case #1 above shows the other 27 cases were not stalled.

## Still unmeasured after this analysis
- The syscall or bash construct the stuck process is actually parked in.
- Whether the survivor is the top-level script process or a forked subshell.
- Whether child_a or position is causal (see #3).

## 6. Correction to #3: neither lead survives the whole log cleanly

`child_a` is not only used by the two failing cases. The same suite also drives it at
`test-issue-73-canonical-root.py:272, 301, 307, 312, 317, 356`, in
`TestBoundRootReachesTheWorkerRecord` and `TestPreservedBehavior`, and every one of those
passed in the very same failing run. (Each class builds its own fixture in its own
`TemporaryDirectory`, so "child_a" is a path shape reused per class, not one directory.)

That also supplies a counterexample to the pure-position reading:
`test_dispatch_into_a_child_worktree_creates_no_worker_record` is the FIRST method of
`TestBoundRootReachesTheWorkerRecord` and it drives child_a - and it passed.

Third observation that constrains any candidate cause: every case in
`TestBindingCompletesAndAccepts` (which ran first, all ok) *accepts* and therefore
executes strictly MORE of `kaola-tmux.sh` than a refusal does, continuing past the guard
to `tmux executable not found`. The cases that hung ran strictly less code than cases
that passed, both before and after them.

Taken together these make a code-path-specific cause unlikely and point at a transient
external condition lasting roughly 120 s that happened to span exactly those two
sequential invocations. The load of ~6.71 came from other work on the machine, since the
reproduction command was a standalone suite run. Mission 1's job is to catch that
transient in the act rather than to keep ranking correlations.
