# Issue #391 finalization

## Delivered

The five Host-wake regression suites now start their carrier targets as real
Hosts. The change is fixture-only (`tests/contract/`, five files): Host
sessions use the documented `<platform>-<CODE>-orchestrator-<purpose>` name
(without the `-i<N>-` worker marker), and the in-process holder in test 173 is
constructed with `session_role="host"`. No holder or CLI behavior changed, so
the #388 role gate is intact: worker and Expert seats still receive no
`--host-entry` and no Host carrier.

The issue's original diagnosis (a sandbox manifest without
`host_skill_entry`) was corrected with evidence: the fixtures read the real
`platforms/<id>.yaml` manifest, which does declare the entry. What they lost
was the standard Host name that #388 uses to derive `session_role=host`.
`test-issue-259` also had to avoid the `-i259-` worker exclusion marker.

## Candidate

- Branch: `workflow/issue-391`
- Base: `3b45c099` (main)
- Candidate: `d3f33006` (`test: name fixture Hosts by the standard Host role (#391)`)

## Evidence

- Five suites individually green: 70 (6/6 tests, 56 checks), 76 (5/5),
  92 (17/17), 173 (10/10), 259 (63 tests OK); logs `/tmp/kpr391-70b.log`,
  `/tmp/kpr391-76.log`, `/tmp/kpr391-92.log`, `/tmp/kpr391-173.log`,
  `/tmp/kpr391-259b.log`.
- `test-issue-388-role-carrier.py`: 7/7 tests OK (`/tmp/kpr391-388.log`),
  proving the #388 role gate was not weakened.
- `./scripts/render-skills.py --check`: PASS.
- Full release gate on the clean candidate: `./scripts/validate.sh`,
  FULL INVENTORY 145 suites, `FULL_VALIDATE_RC=0`, total wall 2015.28 s, no
  FAILED and no flake requiring a rerun (`/tmp/kpr391-full.log`).

## Change scope

Files this branch changed outside the kaola-workflow/ run-state band:

- tests/contract/test-issue-173-codex-system-error-turn.py
- tests/contract/test-issue-259-record-contract.py
- tests/contract/test-issue-70-binding-fact.py
- tests/contract/test-issue-76-permission-wake.py
- tests/contract/test-issue-92-permission-wake-recovery.py

No product code, generated Skill, platform manifest, CHANGELOG, or Seats
surface changed. No install, tag, or release was made.

## Known failures / unverified scope

None observed. The full inventory passed on the exact clean candidate. The
test-70 negative control is a plain live session rather than a second Host
because one repository holds one standard Host; the positive binding
assertion is unchanged.

## Follow-Up Items

None for this issue.

## Final readiness

Ready for the merge sink to publish `d3f33006` to main and close Issue #391,
then archive the run folder and clean up the worktree and branch. Host will run
the final gate on the merged tree.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- tests/contract/test-issue-173-codex-system-error-turn.py
- tests/contract/test-issue-259-record-contract.py
- tests/contract/test-issue-70-binding-fact.py
- tests/contract/test-issue-76-permission-wake.py
- tests/contract/test-issue-92-permission-wake-recovery.py

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-391/.cache/final-validation.md
- kaola-workflow/archive/issue-391/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-391/finalization-summary.md
- kaola-workflow/archive/issue-391/mission-ledger.jsonl
- kaola-workflow/archive/issue-391/workflow-state.md
