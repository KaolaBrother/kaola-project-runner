# Issue #78 — find the real cause of the Issue #73 refusal-path 60 s hang and orphaned kaola-tmux.sh, then fix it minimally

Run: project `issue-78`, branch `workflow/issue-78`,
worktree `/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-78`.
Base: main `f6be8a3` (= origin/main at claim).

Scope guard: write access limited to the shared entrypoint `scripts/kaola-tmux.sh`, its Issue #73
contract test, and any docs that change meaning. Issues #74 / #75 / #69 are owned by other live
sessions — never touch their folders, worktrees, branches, or processes. No finalize, archive, sink,
or issue close in this run; the user accepts first.

Standing constraints from the user brief:
- Do NOT "just raise the timeout", and do NOT add a generic retry or a new guard/classifier layer.
- Keep the Issue #77 test-holder-leak fix (`63736ad`) intact.
- Never kill processes that are not provably this run's own; clean up only after exact identity proof
  and leave a receipt.

Open leads to separate by measurement (both fit the reported data, only one can be causal):
- (a) target identity: both failing cases used `child_a`; the passing drift cases used `child_b` /
  `other_repo`.
- (b) execution position: alphabetically those same two cases are the 1st and 2nd methods in
  `TestBindingRefusesDrift`, so "first invocations in the class" fits equally well.
- (c) the orphan's identity: a SIGKILL to the direct child cannot leave the direct child alive, so
  the survivor is most likely a forked bash subshell (identical `ps` argv), not the top-level script.

---

## 1. Reproduce the hang under bounded induced load, with timepoint evidence
item: Reproduce the >60 s refusal-path hang in an isolated bounded harness and capture where the
  wall clock actually goes inside one `scripts/kaola-tmux.sh <platform> start` refusal invocation —
  per-step timestamps plus a stack/state snapshot of the stuck process at the moment it is stuck.
  Must also record the orphan's real identity: pid, ppid, argv, `pgrep -P`, open files, and whether
  it is the top-level script or a forked subshell. Bound the induced load; never touch processes or
  TMPDIRs that are not this harness's own.
status: in-flight
dispatched: subagent `investigator`, brief "Issue #78 reproduce the refusal-path hang under bounded
  induced load". Output lands at `/tmp/i78-repro/FINDINGS.md`, with raw artifacts under
  `/tmp/i78-repro/` (`trace/`, `stuck/`, `runs/`). Pre-seeded by me: fixture `/tmp/i78-repro/fix`,
  single-shot `/tmp/i78-repro/one.sh`, BASH_ENV xtrace shim `/tmp/i78-repro/trace-env.sh`.
  Baseline already measured by me at base f6be8a3: a single refusal invocation spans 65 ms total
  (codex/pty 1.35 s wall first-run cold, 0.067 s warm for grok/acp), with only two ~21 ms python3
  spawns - so 60 s cannot be arithmetic slowdown and must be a block.
result: DONE. The dispatched investigator was cut off by a session end before writing FINDINGS.md,
  but its raw artifacts survived and carry the answer. Decisive evidence: `/tmp/i78-repro/stuck/`
  holds `sample` output for five processes that were ALREADY hung on this machine (from other runs;
  read only, never signalled) - and every leaf is parked in
  `do_redirections -> do_redirection_internal -> heredoc_write -> write`. Its
  `/tmp/i78-repro/KILL-RECEIPT.txt` shows it only ever SIGTERMed its own marker-tagged cpu burners
  (`I78BURN_I78MARK8c49d99175` / `I78BURN_I78MINId1a6c1a9`); I verified none survive and load is back
  to 2.18. The orphan question is answered: the survivor is the PRE-EXEC FORK CHILD, which is why it
  shows the parent's argv, has no children, and outlives a SIGKILL aimed at the direct child.
  Full write-up: `kaola-workflow/issue-78/evidence/root-cause.md`.

## 2. Name the root cause and separate it from the rival explanations
item: From Mission 1's evidence, state the one causal mechanism and show why the rival leads
  (child_a-vs-child_b, first-two-position, plain slowness under load) are refuted or subsumed.
  A confirmed "cannot reproduce" is an acceptable outcome only with the induced-load envelope that
  was actually reached recorded alongside it.
status: done
dispatched: self (inline, from the investigator's raw artifacts plus my own measurements)
result: ROOT CAUSE = bash here-document self-deadlock on a macOS degraded pipe. Bash 5.3.9 writes any
  heredoc body <= HEREDOC_PIPESIZE (4096 B) into a pipe from the pre-exec fork child, which holds both
  ends, so nothing drains it. Under system-wide pipe-KVA pressure macOS hands out 512-byte pipes - I
  measured the cliff directly: capacity 65536 at 0/50/100 held pipes, 512 at 150, back to 65536 on
  release. The refusal path's `emit_json` heredoc is 883 B > 512, so it deadlocks; the ACCEPTING path
  ends at `die` (plain printf, no heredoc), which is why the cases doing LESS work hung and the ones
  doing more passed. Both rival leads are refuted, not ranked: nothing depends on child_a vs child_b,
  on position, on ACP vs PTY, on the Issue #73 guard, or on Issue #77 - the same deadlock is what has
  `install-local.sh` and a bare `kaola-tmux.sh status --help` hung on this machine for 4 h and 34 h.
  Evidence: `kaola-workflow/issue-78/evidence/root-cause.md`.

## 3. Failing baseline as an executable test
item: Turn the root cause into a test that fails on the unfixed tree and passes only when the cause
  is removed — asserting the refusal terminates and leaves no surviving process, not that it is
  merely faster. Record the failing baseline output at the base SHA.
status: done
dispatched: self (inline). Landed as `tests/contract/test-issue-78-heredoc-deadlock.py`.
result: The test asserts the structural rule "the shared entrypoint carries no here-document and
  no here-string", across `scripts/kaola-tmux.sh` and all nine generated `skills/*/scripts/` copies.
  FAILING BASELINE, proven by restoring f6be8a3 into the worktree and running the new test:
  `Ran 4 tests ... FAILED (failures=10)` - one per file - naming every offender with its size,
  including the actual culprit `line 41 <<PY (883 bytes)` (emit_json) and `line 21 <<EOF (1039
  bytes)` (usage). On the repaired tree: `Ran 4 tests ... OK`.
  Deliberately structural, not behavioural: an end-to-end proof needs machine-wide pipe-KVA
  pressure, which would deadlock OTHER agents' shell scripts, so it must never live in a suite that
  runs on every validate. See the pending decision recorded under Mission 6.

## 4. Minimal production/test repair
item: Fix the named cause in `scripts/kaola-tmux.sh` and/or the Issue #73 test with the smallest
  change that removes it. No timeout inflation as the remedy, no retry loop, no new guard.
status: done
dispatched: self (inline)
result: `scripts/kaola-tmux.sh` - all ten here-documents removed. Nine quoted bodies became
  `"$PYTHON_BIN" -c '<program>' ARGS` (or `printf '%s\n' '...'` for `usage()`), which is already
  this file's own existing idiom at the `json_value`/`payload_hex` helpers; the one expanding
  `read ... <<EOF` became `read ... < <(tmux display-message ...)`, whose writer is a separate
  process that drains concurrently. The conversion is provably semantics-preserving: every quoted
  body was verified to contain zero single quotes and zero backslashes before being wrapped, and
  `sys.argv[1:]` is identical under `-c prog args` and `- args`. Then
  `./scripts/render-skills.py --write` regenerated the nine copies; `--check` PASS.
  No timeout was changed, no retry added, no guard or classifier introduced.
  Byte-identical receipts verified before/after for both the codex/pty and grok/acp refusals, plus
  `usage()` and the unknown-platform `die` path.

## 5. Independent review of the frozen candidate
item: Review the exact frozen candidate SHA for correctness, for whether it truly removes the cause
  rather than masking the symptom, and for test custody (the Issue #73 guard assertions and the
  Issue #77 holder-stop fix must survive unweakened).
status: in-flight
dispatched: subagent `code-reviewer`, on the frozen candidate `9632571` (branch workflow/issue-78,
  parent f6be8a3). Findings land inline in its handback; verdict is mine.
status: done
result: NO DEFECTS. The reviewer verified rather than trusted: byte-identical comparison of all 8
  converted program bodies, empirical `sys.argv[1:]`/`sys.path[0]` equivalence, a 400-iteration
  process-substitution fd/zombie check, `cmp`-identical `usage()` output, and `cmp`-identical
  generated copies. On test custody it PROVED the stub change was necessary rather than weakening,
  by running the OLD stub against the NEW wrapper and reproducing `invalid manifest
  default_transport`; and it confirmed `test-issue-73-canonical-root.py` has 0 diff lines, so the
  #73 guard assertions and the #77 holder force-stop are untouched. My verdict, after reading the
  diff myself: accept.
  Three low-severity observations acted on - the new test's regex now catches `<<\EOF`, `<<'E O F'`,
  `<<"EOF"`, `<<2EOF` and `<<-` while excluding `$((1 << n))` and `#` comments; a tautological
  constant test was deleted; the argv-noise note was accepted with no change.
  The review also surfaced, indirectly, that `scripts/validate.sh` picks suites from explicit lists
  rather than a glob - so the guard was registered nowhere and would never have run. It is now first
  in `python_suites_b` and listed in `python_suites_all`, and proven to execute in a real validate
  run. Details: `evidence/verification.md` round 2.

## 6. Post-fix verification and residue receipt
item: At the frozen SHA run the targeted Issue #73 suite, the full `./scripts/validate.sh`, and a
  bounded concurrent-load measurement matching the reported failure envelope (load ~6.7+). Record
  exact outcomes, plus a receipt for any leftover process or temp dir this run created and removed.
status: done
dispatched: self (inline). Receipts at `kaola-workflow/issue-78/evidence/verification.md` and
  `.../validate-final.log`.
result: Targeted Issue #73 suite `Ran 29 tests in 24.634s / OK` - the normal ~24 s, against the
  145 s of the reported failing run - with zero residual processes and zero residual holders, so
  Issue #77's fix is intact. New suite `Ran 4 tests / OK`, and FAILS on the restored f6be8a3
  baseline with 10 failures. Full `./scripts/validate.sh` -> exit 1 with exactly one failing suite,
  `test-issue-49-grok-bot-host.py`, which is PRE-EXISTING: A/B on the identical tree reproduces the
  same `OSError: [Errno 66] Directory not empty: .../repo/.git` 2/2 on untouched f6be8a3 and 3/3 on
  the fix. It is a TemporaryDirectory cleanup race, unrelated to here-documents, and out of the
  owner-agreed scope.
  SCOPE RULING APPLIED (owner, this run): repair only the shared entrypoint's proven deadlock; do
  NOT extend to `scripts/install-local.sh` or the other test suites - the owner is filing those
  separately. No machine-level pipe fault injection was performed; the structural baseline plus the
  bounded capacity measurement stand in its place.
  Verification also found and repaired two regressions this change itself introduced: the
  `read < <(...)` / `set -e` tolerance loss, and the `test-acp-contract.py` python stub that pinned
  the old `python3 -` calling convention. Both are documented in verification.md section 6.
  RESIDUE RECEIPT: the Mission 1 investigator SIGTERMed only its own marker-tagged cpu burners
  (`I78BURN_I78MARK8c49d99175`, `I78BURN_I78MINId1a6c1a9`) - full list in
  `evidence/mission1-kill-receipt.txt` - and I confirmed none survive. No process belonging to any
  other run was signalled. The pre-existing orphans on this machine (issue-74 pids 21114/21117/21118,
  issue-67 pids 62000/62004/62005, a 34 h `status --help` pair 69036/69044, and issue-71
  install-local.sh 11132/11133) were only READ via `sample`, never signalled; they belong to other
  runs and are left untouched. Scratch dirs created by this run: `/tmp/i78-repro`, `/tmp/i78-backup`,
  `/tmp/i78-backup2`, `/tmp/kaola-i78-*`.
