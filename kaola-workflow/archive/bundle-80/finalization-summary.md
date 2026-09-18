# Finalization summary — Issue #80

Run `bundle-80`, branch `workflow/bundle-80`, base main `f6cbe27`, sink `merge`.
Owner ACCEPT given on frozen candidate `c4caf37`; `93310eb` adds only the
finalization CHANGELOG docking on top.

## Delivered

Issue #80 reported `tests/contract/test-issue-49-grok-bot-host.py` dying in
`TemporaryDirectory` teardown with `OSError: [Errno 66] Directory not empty:
<tmp>/repo/.git` after all 43 assertions passed — reproducibly red on clean
`main`, and hiding every suite after it in `validate.sh`'s lane B.

Measured with `GIT_TRACE2_EVENT`: `git commit` (and `merge`/`rebase`, and
`receive-pack` on push) spawns a **detached** `git maintenance run --auto
--quiet --detach` child that runs `repack --write-midx` + `update-server-info`
inside the fixture `.git` for ~0.44 s after the command returns — the exact
window the test's ~0.45 s of remaining work and teardown overlap. `rmdir(.git)`
meets recreated `info/refs` + `objects/info/packs` → Errno 66.

Fix (+8/−0 lines, test file only): `git()` runs every fixture git call with
`maintenance.auto=false` (`GIT_CONFIG_*` env), and the bare `origin.git` gets
`receive.autogc=false` in repo config — `git push` strips config-env for the
receive-pack child. Measured: `gc.auto=0` and `GIT_AUTO_MAINTENANCE=0` do not
gate the spawn. No `ignore_cleanup_errors`, no sleeps, no assertion changes.

## Files Changed

| file | change |
|---|---|
| `tests/contract/test-issue-49-grok-bot-host.py` | `git()` env gains `GIT_CONFIG_COUNT/KEY_0/VALUE_0 = maintenance.auto=false`; `LocatorFixture` bare repo gains `receive.autogc=false`; two explanatory comments |
| `CHANGELOG.md` | `## Unreleased` entry (finalization docking, `93310eb`) |

## Test Coverage

- The suite itself is the coverage: 43 tests exercise the fixture paths that
  previously raced teardown (`git_repo`, `LocatorFixture`).
- Verified on `c4caf37`: standalone `TMPDIR=<fresh> python3
  tests/contract/test-issue-49-grok-bot-host.py` — 5/5 runs OK, `Ran 43 tests`
  each; traced run shows 0 `maintenance run` spawns (base showed the full
  detach→repack→midx→update-server-info chain).

## Validation

- `./scripts/validate.sh` on `c4caf37`: **exit 0**, zero `FAILED` lines; the
  Issue #80 suite ran `Ran 43 tests` OK inside lane B and every suite ordered
  after it ran. Log: `evidence/validate-final.log`. No interference from the
  parallel #79 run observed during the window.
- `./scripts/render-skills.py --check`: PASS (budgets OK).
- `.cache/final-validation.md`: verdict pass, `validated_candidate_hash`
  `fde70dab…`, command `./scripts/validate.sh`.

## Changed Paths

- `tests/contract/test-issue-49-grok-bot-host.py`
- `CHANGELOG.md`
- (run records under `kaola-workflow/bundle-80/`)

## Documentation Docking

`.cache/doc-docking.md` — DOCKED. `CHANGELOG.md` updated; `README.md` and all
`docs/` surfaces NO IMPACT (no public signature, field, flag, env var, budget,
or validation command changed).

## Acceptance legs

- Automated: 5/5 standalone green, validate.sh exit 0, render --check PASS — recorded above.
- Outer review: ACCEPT on `c4caf37` (the +8/−0 fixture diff and raw evidence were independently reviewed).

## Follow-Up Items

- `filed: #83` (P3) — `run_suite_lane` abandons a validate lane on first
  failure, hiding downstream suites. Flagged in the issue's non-binding remedy
  as a separate decision; kept out of this run's file scope.
- Correction comment posted on #80 recording what the hypothesis turned out to
  be (detached `maintenance run --auto` → `repack --write-midx` →
  `update-server-info`).

## Readiness

All missions done, evidence docked, acceptance recorded. Sink held at the
boundary until the parallel #79 finalization completes its main merge, per
outer instruction; on main movement the plan is rebase `workflow/bundle-80`
onto newest main, rerun standalone + full `validate.sh` on that SHA, then
finalize/archive/sink/closure-audit.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/bundle-80/.cache/doc-docking.md
- kaola-workflow/archive/bundle-80/.cache/final-validation.md
- kaola-workflow/archive/bundle-80/.cache/mirror-digest.json
- kaola-workflow/archive/bundle-80/.cache/origin/selection-record.json
- kaola-workflow/archive/bundle-80/evidence/candidate-diff.txt
- kaola-workflow/archive/bundle-80/evidence/verification.md
- kaola-workflow/archive/bundle-80/finalization-summary.md
- kaola-workflow/archive/bundle-80/mission-list.md
- kaola-workflow/archive/bundle-80/workflow-state.md
