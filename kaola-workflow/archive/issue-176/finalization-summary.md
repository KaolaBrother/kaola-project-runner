# Finalization summary — issue-176

## Delivered

Issue #176 root-caused and fixed. `test-issue-65-host-contract.py` failed with
`no-session` on `send` because its `cli()` copied the inherited environment: a
focused run from a dispatched seat inherits `KAOLA_ACP_HEARTBEAT_HOST` +
`KAOLA_ACP_DISPATCHER` (naming different holders), so the fixture `start` was
refused `heartbeat-host-conflict` before anything was spawned. A typed refusal
reports `result: "refused"` with no `error` key, so the suite's error-only
check passed the refused start and the failure surfaced later at `send` as
`no-session`. The mechanism pre-exists at base `2e18946`; it is not a boot
race and was not resolved by #174's ordering fix. The suite now drops the
inherited `KAOLA_*` namespace and sets its one fixture (the
`test-issue-98-dsh-acp.py` pattern, the rule `validate.sh` applies per #115),
and its `cli()` fails a typed refusal at the command that was refused.

Candidate: workflow/issue-176 @ 10402a0 (rebased onto main 10b8379; the test
file is byte-identical to reviewed commit b482925; both Unreleased CHANGELOG
entries kept). Acceptance: independent Claude Code review verdict PASS
("VERDICT: PASS for issue #176"; reviewer reproduced old and new suite
behavior from its own dispatched seat). Correction comment posted on #176
before closure (issuecomment-5835493255), correcting the issue's "Cursor CLI
dependent" misdiagnosis and recording the review PASS.

Acceptance legs: automated — full `./scripts/validate.sh` green at rest on the
rebased candidate (exit 0, 0 FAILED/SKIPPED, log /tmp/kpr-i176-validate-final2.log)
and under concurrent load (/tmp/kpr-i176-validate-load.log, exit 0); focused
loops 0/12 → 12/12 at rest and 12/12 under load
(/tmp/kpr-i176-loop-rest.log, /tmp/kpr-i176-loop-fixed-rest.log,
/tmp/kpr-i176-loop-fixed-load.log); manual/UAT — none owed for a test-only
change; unexecuted — none.

## Files Changed

- `tests/contract/test-issue-65-host-contract.py` (+11/−1): env scrub of the
  inherited `KAOLA_*` namespace plus a typed-refusal check in `cli()`.
- `CHANGELOG.md` (+22): Unreleased entry for #176 with evidence and Seats
  line (`Seats: restart not required`; operator test diff set empty — no
  holder, bridge, adapter, or platform bytes changed).

Net: +33/−1 across two files. No scripts, templates, or generated surfaces
changed; no re-render needed.

## Test Coverage

The suite under repair is its own coverage: all 13 tests green, including the
live `CursorAnchorBehaviour` anchor test (green inside validate at rest and
under load). The refusal guard is exercised by construction: any refused
start now fails at `start` with its reason instead of degrading to
`no-session` at `send`. Loop evidence: 12/12 at rest, 12/12 under concurrent
full validate (0/12 before the fix).

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- tests/contract/test-issue-65-host-contract.py

## Documentation Docking

DOCKED — `.cache/doc-docking.md`: CHANGELOG entry added; README, docs/api.md,
docs/, and AGENTS.md checked with no impact (test-only change; the typed
refusal receipt shape is already the documented, unchanged contract).

## Follow-Up Items

- Filed #182 (labels: bug, P2): sibling live suites that build command env
  with `env = dict(os.environ)` fail the same way from dispatched seats;
  measured on `test-issue-65-steering.py` (18 failures + 2 errors, dominant
  `no-session` on `send`) at commit 10402a0; duplicate probe recorded in its
  body. Not in this issue's scope: #176 fixed only the 65-host-contract suite.

## Readiness

Ready. All missions done (ledger 3/3 done), final validation pass, docs
docked, review PASS, correction comment posted, follow-up filed. Sink: merge
of workflow/issue-176 to main, closing #176; no PR, no release, no tag, no
pin.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-176/.cache/doc-docking.md
- kaola-workflow/archive/issue-176/.cache/final-validation.md
- kaola-workflow/archive/issue-176/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-176/finalization-summary.md
- kaola-workflow/archive/issue-176/mission-ledger.jsonl
- kaola-workflow/archive/issue-176/workflow-state.md
