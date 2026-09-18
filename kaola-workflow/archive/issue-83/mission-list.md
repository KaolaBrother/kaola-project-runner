# Issue #83: run_suite_lane abandons a validate lane on first failure, hiding downstream suites

Scope: `scripts/validate.sh` only, plus focused test/evidence. Worktree:
`.kw/worktrees/issue-83`, branch `workflow/issue-83`. Other runs (#69/#74/#75/#81/#82)
own separate files/runs — do not touch.

- item: Reproduce failure-first — inject a temporary failing suite into a lane in the worktree and show downstream suites never run and the replay dies on `cat: ... No such file or directory`; capture raw log evidence.
  status: done
  dispatched: self
  result: focused test (extracts real lane block, drives stub suites) fails pre-fix exactly as the issue describes — `FAILED:` lines then `cat: s-a2.py.log: No such file or directory`, replay truncated, downstream markers absent; green path passes. Raw output: `kaola-workflow/issue-83/evidence/focused-test-prefix.log` at base c963bade.
- item: Implement scoped fix in `scripts/validate.sh` — lane runs every suite and accumulates failures (`FAILED:` per suite, nonzero at lane end); ordered replay prints explicit `SKIPPED:` for any missing log instead of a bare cat error, and forces nonzero; green path output unchanged.
  status: done
  dispatched: self
  result: `run_suite_lane` accumulates `status` and returns it after the loop (no early return); replay guards `cat` with `[[ -f ]]`, else prints `SKIPPED: <suite> (suite never ran; no log)` and sets `python_status=1`; comment updated; new test registered in `python_suites_all` + lane A. `bash -n` clean.
- item: Add committed focused test covering the new contract (a failing suite does not hide downstream suites; a missing log is reported SKIPPED, not a cat error; overall stays nonzero; green path passes).
  status: done
  dispatched: self
  result: `tests/contract/test-issue-83-lane-failure-visibility.py` — 3 tests, all pass post-fix (0.17s): failure does not hide downstream suites, missing log → SKIPPED + nonzero, green path unchanged.
- item: Run `render-skills.py --check`, the focused test, and full `scripts/validate.sh` in the worktree; freeze exact SHA, diff, and raw logs under `kaola-workflow/issue-83/evidence/`; report for outer acceptance.
  status: done
  dispatched: self
  result: render --check PASS; focused test 3/3 PASS post-fix; real validate with an injected failing suite rc=1 showing `FAILED:` + every downstream suite ran and replayed (no cat errors, no SKIPPED); full green validate rc=0 incl. grok-bot verify PASS. Committed `af3af6e` on `workflow/issue-83`; worktree clean. Evidence: `kaola-workflow/issue-83/evidence/` (base/head SHA, commit diff, pre/post focused logs, failure-path + green validate logs). Injection fully reverted; stub deleted. Awaiting outer acceptance — no finalize/archive/sink performed.

Review round 1 (outer review of `af3af6e`): SKIPPED parenthetical claimed
"(suite never ran; no log)" — an unproven fact (a suite can run and lose its
log; the test's log-eater is exactly that). Fixed in `a0833d8`: message is now
`SKIPPED: <suite> (no log; execution status unknown)`. Comment and test
assertions already said only "left no log" — verified unchanged. render
--check PASS; focused test 3/3 PASS; full validate not re-run — the change is
one printf string literal, focused test exercises that exact branch and
asserts the emitted marker. Evidence refreshed: `head-sha.txt` = a0833d8,
`commit-a0833d8.diff`, `focused-test-postfix.log`, `worktree-status.txt`
(clean). Awaiting outer acceptance.
