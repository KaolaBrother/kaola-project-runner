# Issue #78 verification receipts

Base: main `f6be8a3` (= origin/main at claim). Machine: 10-core Apple Silicon, macOS 27.0,
Homebrew `bash 5.3.9(1)-release`, Python 3.14.3.

## 1. Failing baseline of the new test, at f6be8a3

Produced by restoring the base files into the worktree and running the new suite unchanged:

    $ git checkout -- scripts/kaola-tmux.sh skills
    $ grep -cE "<<'?[A-Za-z_]" scripts/kaola-tmux.sh
    10
    $ python3 tests/contract/test-issue-78-heredoc-deadlock.py
    ...
    AssertionError: Lists differ: [(21, 'EOF', 1039), (41, 'PY', 883), ...] != []
    - [(21, 'EOF', 1039),
    -  (41, 'PY', 883),      <- emit_json, the site that hung the Issue #73 refusals
    -  (121, 'PY', 210),
    -  (259, 'PY', 134),
    -  (343, 'EOF', 212),
    -  (374, 'PY', 523),
    -  (450, 'PY', 333),
    -  (471, 'PY', 909),
    -  (486, 'PY', 451),
    -  (590, 'PY', 287)]
    Ran 4 tests in 0.004s
    FAILED (failures=10)

Ten failures = the source file plus its nine generated `skills/*/scripts/` copies.

On the repaired tree: `Ran 4 tests in 0.002s / OK`, and `grep -cE "<<'?[A-Za-z_]"` returns 0.

## 2. Bounded pipe-capacity measurement (the kernel half of the cause)

Held filled pipes open in one process and measured a freshly created pipe each time. No
machine-level fault injection was performed against any other process, and every held pipe
was released in a `finally`:

    held_pipes  fresh_pipe_capacity
             0  65536
            50  65536
           100  65536
           150  512      <- below the 1039-byte usage() body and the 883-byte emit_json body
    released all held pipes; capacity now: 65536

## 3. Behaviour preserved across the repair

Byte-identical receipts before and after, same fixture, same environment:

    codex / pty  canonical-root-mismatch refusal   identical JSON receipt
    grok  / acp  canonical-root-mismatch refusal   identical JSON receipt
    kaola-tmux.sh codex status --help              usage text unchanged
    kaola-tmux.sh nosuch start                     "kaola-tmux[nosuch]: unknown platform: nosuch"

## 4. Targeted Issue #73 suite

    $ TMPDIR=/tmp/kaola-i78-t1 python3 tests/contract/test-issue-73-canonical-root.py
    Ran 29 tests in 24.634s
    OK

24.6 s is the normal figure the Issue #78 report cites (~24 s), against the 145 s of the
failing run. Residue afterwards: none.

    $ LC_ALL=C ps -eo pid,lstart,command | grep "kaola-i78-t1" | grep -v grep
      NONE
    $ LC_ALL=C ps -eo pid,lstart,command | grep "worktrees/issue-78" | grep -v grep | grep -v "claude "
      NONE

Issue #77's `addCleanup` holder force-stop is untouched and still leaves zero holders.

## 5. Full validate at the frozen tree

`scripts/validate.sh` -> exit 1, with exactly one failing suite:

    FAILED: test-issue-49-grok-bot-host.py

    render-skills: PASS
    installer migration acceptance: PASS
    installer runtimes acceptance: PASS

### That one failure is PRE-EXISTING, not caused by this change

Proven by A/B on the identical tree. Restoring the base files and re-running the same suite
reproduces it exactly:

    BASELINE f6be8a3 run 1: OSError: [Errno 66] Directory not empty: '/tmp/kaola-i78-gb1/tmpbi1gtdi2/repo/.git'
                            Ran 43 tests in 20.389s / FAILED (errors=1)
    BASELINE f6be8a3 run 2: OSError: [Errno 66] Directory not empty: '/tmp/kaola-i78-gb2/tmpe5pu8ar2/repo/.git'
                            Ran 43 tests in 19.742s / FAILED (errors=1)

    ON THE FIX     run 1-3: same test, same OSError, 43 tests, FAILED (errors=1) each time

It is a `tempfile.TemporaryDirectory` cleanup race on a `repo/.git` directory in
`Issue49PinModel.test_content_stage_is_not_saveable_and_require_pinned_refuses_it`
(`test-issue-49-grok-bot-host.py:645`), reproducible 3/3 on the fix and 2/2 on the untouched
baseline. It is unrelated to here-documents and out of this run's agreed scope; it is left for
the separate issue the owner is filing.

## 6. Regressions this change introduced and then repaired

Both were found by my own verification, not by the suite alone.

1. `read ... < <(cmd)` is not the heredoc it replaced. A heredoc always supplies a trailing
   newline, so `read` returned 0 and left the fields empty when tmux produced nothing; a
   process substitution yields EOF, `read` returns 1, and `set -e` then exits the script.
   Demonstrated directly:

       OLD shape: read rc=0 A=[] B=[]; script continued
       NEW shape: exit=1

   Repaired by appending `|| true`, which restores the original tolerance exactly.

2. `test-acp-contract.py::Issue39HolderInstanceTests::test_shell_wrapper_forwards_expected_flag`
   failed with `kaola-tmux[grok]: invalid manifest default_transport`. Its Python stub
   recognises the manifest read by `[ "$1" = "-" ]`, which pins the old calling convention; with
   `-c` the stub fell through and echoed the program text as the transport value. The stub now
   accepts both spellings. The assertion it makes - that the wrapper forwards
   `--expected-holder-instance-id` - is unchanged. After the repair:

       Ran 1 test in 0.811s
       OK

## 7. What was NOT proven

No end-to-end behavioural reproduction of the deadlock was run. Producing one requires
machine-wide pipe-KVA pressure, which would deadlock other agents' shell scripts on this
shared machine; the owner ruled that out, and the structural baseline in section 1 plus the
bounded capacity measurement in section 2 stand in its place. The causal chain is therefore
established by: the live `sample` stacks of five already-hung processes, the measured pipe
cliff, and the measured here-document sizes - not by a staged end-to-end hang.

---

# Round 2: independent review of frozen candidate 9632571, and what it changed

## Review outcome

A `code-reviewer` subagent reviewed `9632571` against parent `f6be8a3` in a clean context and
found **no defects**. It verified independently rather than taking the commit message's word:

- All 8 converted Python bodies are **byte-identical** to their old heredoc bodies (mechanical
  extraction and compare); zero single quotes, zero backslashes, no `sys.argv[0]` use.
  `sys.argv[1:]` equivalence confirmed empirically, and `sys.path[0]` is `''` under both spellings,
  so `bootstrap_relay`'s `spec_from_file_location` import is unaffected.
- No converted program touches stdin, and `kaola-relay-protocol.py` (the only foreign module one of
  them loads) has no stdin access or top-level I/O.
- `read` still runs in the current shell, so its assignments persist; every `STATE_*` is reset at
  `scripts/kaola-tmux.sh:335-341` before use, so `|| true` cannot leave a stale value. A
  400-iteration process-substitution loop leaked no file descriptors and no zombies - which matters
  because `load_session_identity` is polled up to ~200x in the start loop.
- `usage()` output is `cmp`-identical to the old `cat` output, rc=2 in both.
- The `|| die "model contains unsupported terminal controls"` path still fires (`MODEL_VALUE=$'a\tb'`
  gives rc=1).
- All nine `skills/*/scripts/kaola-tmux.sh` are `cmp`-identical to the source.
- **Test custody:** the reviewer proved the stub change was *necessary*, not a weakening, by running
  the OLD stub against the NEW wrapper and reproducing `invalid manifest default_transport` (rc=1).
  The assertions - `assertIn("kaola-acp.py", argv[0])` and exact `--expected-holder-instance-id`
  forwarding including the empty value - are unchanged. `test-issue-73-canonical-root.py` has **0
  diff lines**, so the Issue #73 guard assertions and the Issue #77 `addCleanup` force-stop are
  untouched.

## Three low-severity observations acted on

1. The new test's opener regex missed heredoc spellings bash accepts. Hardened to detect
   backslash-escaped tags (`<<\EOF`), quoted tags containing spaces (`<<'E O F'`), double-quoted
   tags, digit-leading tags (`<<2EOF`) and the `<<-` dash form, while excluding an arithmetic left
   shift (`$((1 << n))`) and a `#` comment that merely quotes `<<`. Verified case by case:

       backslash-escaped tag        -> [(1, 'EOF', 5)]
       quoted with spaces           -> [(1, 'E O F', 5)]
       digit-leading tag            -> [(1, '2EOF', 5)]
       dash form                    -> [(1, 'EOF', 5)]
       double-quoted tag            -> [(1, 'EOF', 5)]
       arithmetic shift             -> []
       comment mentioning <<EOF     -> []
       here-string                  -> [(1, '<<<', 0)]

   Re-confirmed it still finds all **10** here-documents in the f6be8a3 entrypoint.
2. `test_the_deadlock_window_is_stated_correctly` asserted `512 < 4096` over two constants declared
   ten lines above it. Removed as a tautology with no regression value.
3. The reviewer's note that `python3 -c` now carries up to 908 bytes of program text in argv is
   accepted with no change: nothing in the repo matches on `kaola-tmux.sh` argv
   (`--exact-process-title` in `kaola-pane-relay.py` matches the pane child only). The practical
   consequence is only that `ps -ww` output for these children is noisier.

## A gap the review surfaced indirectly, now closed

`scripts/validate.sh` selects suites from explicit lists, not a glob, so the new guard was
registered nowhere and would never have run in validation. It is now first in `python_suites_b`
(it costs 3 ms, so it fails fast) and listed in `python_suites_all` for log output. Proven to
execute inside a real validate run:

    test_every_generated_copy_is_covered ... ok
    test_no_here_document_anywhere_in_the_shared_entrypoint ... ok
    test_the_entrypoint_exists ... ok
    Ran 3 tests in 0.002s
    OK

## Final validate at the accepted tree

`./scripts/validate.sh` -> exit 1, with exactly one failing suite, the pre-existing
`test-issue-49-grok-bot-host.py` documented in section 5 above. Log:
`kaola-workflow/issue-78/evidence/validate-final.log`.
