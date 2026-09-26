# Finalization Summary — Issue #182

## Delivered

Tests-only fix per the owner diagnosis comment (#issuecomment-5842545375), on branch
`workflow/issue-182` @ `32de45f` (base `b13a3a8`), worktree
`.kw/worktrees/issue-182`:

- **Pattern A (18 sites):** every contract-suite fixture that built a spawned
  `kaola-acp.py` command env from `os.environ` now builds it as
  `{k: v for k, v in os.environ.items() if not k.startswith("KAOLA_")}` and re-sets its
  own suite fixtures — 17 fixture swaps across 13 files (acp-contract ×2, follow,
  holder-continue, sweep, watch fixture, droid, 22, 33, 65-steering, 95, 73 ×3 replacing
  the partial #104 pops, 64, progressive ×2), plus `test-zcode-acp-contract.py`'s
  `test_resolve_runtime_fails_closed` wrapped in `mock.patch.dict(..., clear=True)`
  without `KAOLA_ZCODE_ENTRY`/`KAOLA_ZCODE_NODE`. The two watch installer sites
  (`:643`/`:685`) keep `dict(os.environ)` per the diagnosis.
- **Pattern B (10 helpers):** fail on `result == "refused"` when `check=True` — acp-contract
  ×2 (incl. the `kwargs.get("check", True)` variant), follow, holder-continue, watch,
  droid, 33, 65-steering, 73, 95 — so a typed refusal surfaces at the command that was
  refused instead of later as `no-session`.
- **Transitive:** `test-issue-130-pty-retired.py` (49 tests, untouched) is fixed through
  `test-acp-contract.py`.
- **CHANGELOG:** Unreleased entry for #182, `Seats: restart not required`, empty
  operator test.
- Net vs base: `tests/contract` +55/−28 (= +27) across 14 files; CHANGELOG +19; total
  +74/−28. No production, template, adapter, or generated-surface change.

## Files Changed

- `CHANGELOG.md`
- `tests/contract/test-acp-contract.py`
- `tests/contract/test-acp-follow-contract.py`
- `tests/contract/test-acp-holder-continue.py`
- `tests/contract/test-acp-sweep-contract.py`
- `tests/contract/test-acp-watch-contract.py`
- `tests/contract/test-droid-acp-contract.py`
- `tests/contract/test-issue-22-bypass-all-approvals.py`
- `tests/contract/test-issue-33-config-meta.py`
- `tests/contract/test-issue-64-receipt-bound.py`
- `tests/contract/test-issue-65-steering.py`
- `tests/contract/test-issue-73-canonical-root.py`
- `tests/contract/test-issue-95-reader-exception.py`
- `tests/contract/test-progressive-disclosure.py`
- `tests/contract/test-zcode-acp-contract.py`

## Test Coverage

All 15 suites green BOTH ways with identical counts (all rc=0):

| Suite | Inherited (6 `KAOLA_*`) | Dropped (`env -u` all 6) |
|---|---|---|
| acp-contract | OK 69 | OK 69 |
| follow | OK 12 | OK 12 |
| holder-continue | OK 29 | OK 29 |
| sweep | OK 3 | OK 3 |
| watch | OK 13 | OK 13 |
| droid | OK 18 | OK 18 |
| issue-22 | OK 12 | OK 12 |
| issue-33 | OK 9 | OK 9 |
| issue-65-steering | OK 27 | OK 27 |
| issue-95 | OK 2 | OK 2 |
| issue-73 | OK 31 | OK 31 |
| issue-64 | OK 6 | OK 6 |
| progressive | OK 15 | OK 15 |
| zcode | OK 77 | OK 77 |
| issue-130 (transitive) | OK 49 | OK 49 |

`./scripts/validate.sh` from the branch worktree: green end-to-end — render-check PASS,
12/12 validate-skill PASS, installer-migration + installer-runtimes PASS, 61 suites with
0 FAILED/SKIPPED/ERROR (untouched `test-issue-146-session-new-wait.py` passed under
validate's sandboxed HOME), `kaola-grok-bot-verify` PASS, `git diff --check` clean,
clean holder sweep. `./scripts/render-skills.py --check` PASS with no generated-surface
changes.

Acceptance legs: automated (above); close-gate review by the Claude Code seat —
verdict PASS, both-way counts independently confirmed, nits non-blocking.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- tests/contract/test-acp-contract.py
- tests/contract/test-acp-follow-contract.py
- tests/contract/test-acp-holder-continue.py
- tests/contract/test-acp-sweep-contract.py
- tests/contract/test-acp-watch-contract.py
- tests/contract/test-droid-acp-contract.py
- tests/contract/test-issue-22-bypass-all-approvals.py
- tests/contract/test-issue-33-config-meta.py
- tests/contract/test-issue-64-receipt-bound.py
- tests/contract/test-issue-65-steering.py
- tests/contract/test-issue-73-canonical-root.py
- tests/contract/test-issue-95-reader-exception.py
- tests/contract/test-progressive-disclosure.py
- tests/contract/test-zcode-acp-contract.py

## Documentation Docking

DOCKED — see `.cache/doc-docking.md`. CHANGELOG updated for #182
(`Seats: restart not required`, empty operator test); no other surface impacted because
the run is tests-only.

## Follow-Up Items

None filed. No run-discovered defect outside the diagnosis scope surfaced: the
pre-existing standalone `test-issue-146-session-new-wait.py` install-skew (explicitly
out of scope per the dispatch) did not reproduce under `./scripts/validate.sh`'s
sandboxed HOME, where the suite passed.

## Readiness

Ready: candidate frozen at `32de45f`, working tree clean, ledger 3/3 done,
validation recorded and bound to the candidate tree — proceed to the merge sink.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-182/.cache/doc-docking.md
- kaola-workflow/archive/issue-182/.cache/final-validation.md
- kaola-workflow/archive/issue-182/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-182/finalization-summary.md
- kaola-workflow/archive/issue-182/mission-ledger.jsonl
- kaola-workflow/archive/issue-182/workflow-state.md
