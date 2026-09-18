# Issue #80 — find why test-issue-49-grok-bot-host.py teardown hits Errno 66 on repo/.git, then fix it minimally

Run: project `bundle-80`, branch `workflow/bundle-80`,
worktree `/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/bundle-80`.
Base: main at claim (see workflow-state.md).

Scope guard: write access limited to `tests/contract/test-issue-49-grok-bot-host.py` and strictly
necessary adjacent test helpers. Issues #79 / #74 / #75 / #69 are owned by other live sessions —
never touch their folders, worktrees, branches, files, or processes. No finalize, archive, sink,
or issue close in this run; the outer orchestrator accepts first.

Standing constraints from the user brief:
- Do NOT mask with `ignore_cleanup_errors`; do NOT add blind sleep/timeout.
- Prove the 43 existing assertions are not weakened; single-file runs must pass repeatedly.
- Run `./scripts/render-skills.py --check`; run `./scripts/validate.sh` when safe — if the parallel
  #79 run perturbs it, record exactly and rerun at a safe point.
- Keep sanitized reproduction evidence, the frozen candidate SHA, and the actual diff for the
  outer report.

Issue facts (forge): at main `f6be8a3` and at #78 candidate `9b40638`, 5/5 runs of
`TMPDIR=<fresh> python3 tests/contract/test-issue-49-grok-bot-host.py` end all 43 assertions
green then die in `TemporaryDirectory` cleanup: `OSError: [Errno 66] Directory not empty:
<tmp>/repo/.git` via `tempfile._rmtree` -> `shutil._rmtree_safe_fd_step` -> `os.rmdir`. This makes
`./scripts/validate.sh` exit 1 on clean main and hides every suite ordered after it in
`python_suites_b`. Unconfirmed hypothesis: a background `git` child (e.g. auto-`gc` spawned by the
fixture's own `git` calls) still writes into `.git` while `rmtree` removes it.

---

## 1. Reproduce Errno 66 and capture what is inside repo/.git plus which process wrote it
item: Re-run the exact reported command on a fresh TMPDIR in the bundle-80 worktree; on failure,
  preserve the leftover `repo/.git` contents and identify the creating process (lsof/ps evidence),
  per the issue's "measure first" remedy. Sanitized artifacts land under
  `kaola-workflow/bundle-80/evidence/` plus a raw dir outside the repo.
status: done
dispatched: self
result: Reproduced 2/2 at base f6cbe27 (Errno 66 on `<tmp>/repo/.git`, 43 tests ran, errors=1).
  Leftover `.git` held recreated `info/refs` + `objects/info/packs` = update-server-info output.
  GIT_TRACE2_EVENT proved the chain: fixture `git commit` -> detached
  `git maintenance run --auto --quiet --detach` -> `git repack -d -l --cruft --write-midx`
  (pack-objects 1345 objs + multi-pack-index write + update-server-info) writing `.git`
  concurrently with rmtree. Post-commit test work is ~0.45 s, overlapping repack's ~0.44 s tail.

## 2. Minimal root-cause fix in the test fixture
item: Change only what the measured root cause requires inside
  `tests/contract/test-issue-49-grok-bot-host.py` (and an adjacent helper only if the fixture lives
  there). No `ignore_cleanup_errors`, no blind sleep/timeout, no assertion changes.
status: done
dispatched: self
result: +8/-0 lines in the test file only. `git()` env gains
  `GIT_CONFIG_COUNT/KEY_0/VALUE_0 = maintenance.auto=false` (measured: `gc.auto=0` and
  `GIT_AUTO_MAINTENANCE=0` do NOT gate the spawn; `maintenance.auto=false` does). LocatorFixture's
  bare origin.git gets repo-config `receive.autogc=false` because `git push` unsets
  `GIT_CONFIG_COUNT` for the receive-pack child (measured via hook env + bare-repo config).

## 3. Prove the fix on the frozen candidate
item: On the frozen candidate SHA: the same standalone command passes N consecutive runs with all
  43 tests green (assertions unchanged vs base), plus `./scripts/render-skills.py --check` clean.
status: done
dispatched: self
result: Frozen candidate `c4caf37` on `workflow/bundle-80` (base `f6cbe27`). 5/5 standalone runs
  OK, `Ran 43 tests` each; one run under GIT_TRACE2_EVENT shows 0 `maintenance run` spawns
  (base run showed the full commit→detach→repack→midx→update-server-info chain).
  `render --check` PASS. Diff is +8/−0, assertions untouched.

## 4. Integration validation via validate.sh
item: Run `./scripts/validate.sh` in the worktree; if the parallel #79 run perturbs shared
  resources, record the exact interference and rerun at a safe point. Record exact outcome.
status: done
dispatched: self
result: `./scripts/validate.sh` exit 0 on `c4caf37` — zero `FAILED` lines, Issue #80 suite
  `Ran 43 tests` OK in lane B and all downstream suites ran. No #79 interference observed
  (its validate was not executing during this window; its orphan acp-holders were left alone).
  Log: `evidence/validate-final.log`.

## 5. Package evidence and report to the outer orchestrator
item: Write sanitized reproduction + fix evidence under `kaola-workflow/bundle-80/evidence/`,
  record frozen candidate SHA and the actual diff; report back. No finalize/archive/sink before
  outer ACCEPT.
status: done
dispatched: self
result: `evidence/verification.md` + `evidence/candidate-diff.txt` + `evidence/validate-final.log`
  written; candidate `c4caf37` + diff + verification reported to the outer orchestrator in
  this session's reply. Standing by for ACCEPT or rework — no finalize/archive/sink.
