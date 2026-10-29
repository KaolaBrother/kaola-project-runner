# Finalization Summary — issue-424

## Delivered

`scripts/validate.sh` now registers `test-issue-264-compact-recovery.py` in both
Python groups — appended at the end of `python_suites_all` (after
`test-issue-423-devin-compaction-summary.py`) and at the end of `python_suites_b`
— mirroring the 423 registration exactly as the issue's remedy proposed. The 49
Issue #264 compaction-classifier tests (per-platform classifier, reload tracker,
ZCode compact mapping) now execute under both the whole inventory and `--suite`,
because `resolve_suite`/`--list` walk `python_suites_all` only.

Host self-executed this two-line registration (simple authorized work; no worker
dispatch — count ceiling not a target). CHANGELOG: no entry (repo dev tooling
only; no installed Skill payload, holder, bridge, quota, adapter, or platform
surface changed; no seats-restart implication). Docs: unaffected.

## Candidate

- Branch `workflow/issue-424`, commit `c19cb5db` (1 file, +3/−1: `scripts/validate.sh`)
- Base: main `ace2ffee` (clean, synchronized 0/0 at claim)

## Evidence

All measured in the candidate worktree at `c19cb5db`:

- `./scripts/validate.sh --list` names the suite; inventory count 172 (was 171).
- `./scripts/validate.sh --suite test-issue-264-compact-recovery.py` →
  `Ran 49 tests in 0.501s / OK`, exit 0.
- `./scripts/validate.sh --suite test-issue-264-validate-lane-integrity.py` → exit 0
  (registration lane-consistent).
- `./scripts/validate.sh --suite test-issue-423-devin-compaction-summary.py` → exit 0
  (adjacent suite unaffected; #423 changed its Devin fixtures).
- Standalone baseline at main `ace2ffee` before the change:
  `python3 -m unittest tests.contract.test-issue-264-compact-recovery` →
  `Ran 49 tests … OK` (passes unregistered — registration-only fix, as the issue measured).
- Recorded verdict: `.cache/final-validation.md` (pass, candidate hash bound).

## Known failures / unverified scope

- Whole-inventory `./scripts/validate.sh` (172 suites) was not rerun this run;
  focused validation covers the changed surface per the validation policy. The
  newly registered suite itself and both neighbors are green on the candidate.
- Host heartbeat reconciliation on -dev retired 7 stale accepted-done rows + 1
  inapplicable alert; 11 accepted-done rows remain (warn-level) behind the
  retire route gap filed as #426.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- scripts/validate.sh

## Follow-Up Items

- Filed #426 (P3): accepted-done heartbeat rows cannot retire when dispatch
  sessions are gone from `--live` (collect stopped/completed shape; missing
  index refs). Confirmed created with non-empty body and P3 label.

## Final readiness

Ready: mission ledger 1 done / 0 in-flight; candidate frozen at `c19cb5db`;
acceptance basis of issue #424 met (registration + proof the 49 tests run);
sink = merge to main, close #424, archive/sink on -dev.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-424/.cache/final-validation.md
- kaola-workflow/archive/issue-424/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-424/finalization-summary.md
- kaola-workflow/archive/issue-424/mission-ledger.jsonl
- kaola-workflow/archive/issue-424/workflow-state.md
