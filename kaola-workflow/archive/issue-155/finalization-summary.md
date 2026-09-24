# Finalization summary — issue-155

Issue #155 "docs: api.md opencode steering note still names acp_verified_versions 2.0.11 (record
moved to 2.0.15 in #153)". The Host accepted commit `9eb28d0` on `workflow/issue-155` on
2026-09-24. Disposition: close #155 after the sink-merge (fast-forward of main 26cee00 → 9eb28d0).

## Delivered

- `docs/api.md` opencode steering note: the current-record attribution changed from
  `acp_verified_versions` "names 2.0.11" to "names 2.0.15 (record-only since the 2026-09-24 Pink
  batch)". The dated facts stay: the 1.18.17 `-32601` probe, the 2.0.11 `initialize` observation
  (no steering `_meta`), and the fact that no steering method was re-probed on either newer build.
  The capability claim is unchanged: opencode native steering is `unknown`, the Runner reports
  `steer-capability-unknown` instead of a proven absence, and the manifest is still the single
  source of truth.

Issue statement walk:

| Issue part | Satisfied by |
|---|---|
| Name 2.0.15 as the record | docs/api.md diff at 9eb28d0 ("`acp_verified_versions` names 2.0.15") |
| Keep 1.18.17 (dated probe) and 2.0.11 (dated initialize observation) | Same sentence keeps both; the #88 needle test `test_opencode_unknown_stays_documented_with_its_versions` passes inside validate.sh |
| Keep the capability claim intact | "it is `unknown`", `steer-capability-unknown`, and "instead of a proven absence" are unchanged; ApiDocDefersToTheManifests passes |
| Then ./scripts/validate.sh | rc=0 (see Validation) |

## Files Changed

- `docs/api.md` (+5/−3), and nothing else.

## Test Coverage

No new tests are owed. The existing #88 assertions in
`tests/contract/test-issue-88-permission-defaults.py` (`ApiDocDefersToTheManifests`) read
docs/api.md and pin the dated needles (1.18.17, 2.0.11, steer-capability-unknown, "instead of a
proven absence"). All of them pass on the candidate. The tests were not modified.

## Validation

Candidate `9eb28d0` (worktree `.kw/worktrees/issue-155`, clean). The receipt is
`.cache/final-validation.md`: `verdict: pass`, `validated_candidate_hash
4d0d89e4eae4fe9227fe825db3677a96a24e442f7379593d10d0e31b1b595dbc`.
- `./scripts/render-skills.py --check` → rc=0 (PASS; budgets OK; the grok-bot bridge is at
  content stage, unpinned).
- `./scripts/validate.sh` → rc=0, with a 751-line log at `/tmp/kpr-155-validate.log`. No lane
  failed. The named skips are expected under #151: watchdog on bash 3.2, Python < 3.10 probes,
  and no tmux installed.
- Merged state: main is at 26cee00, the parent of 9eb28d0, so the sink is a fast-forward. The
  merged tree is byte-identical to the validated candidate, and this evidence applies to it
  unchanged.
- run-chains: `chains_config_missing`. This is a consumer repo with no `test:kaola-workflow:*`
  scripts, so finalize gates on the recorded final-validation.md.

## Changed Paths

- docs/api.md

## Documentation Docking

DOCKED; see `.cache/doc-docking.md`.

## Follow-Up Items

None. No run-discovered defects. The parallel #157 run (templates/platforms/tests) was not
touched.

## Measured

- The validate.sh and render-skills.py --check rc values above were measured at 9eb28d0 on
  2026-09-24, on the Mac Studio.
- The only stale attribution in docs/api.md was found with `grep -n "2\.0\.11\|2\.0\.15\|1\.18\.17" docs/api.md`
  at 26cee00 (1 hit, line 450).

## Readiness

Ready: Host acceptance granted, validated, docked. Sink: merge (fast-forward) and close #155.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-155/.cache/doc-docking.md
- kaola-workflow/archive/issue-155/.cache/final-validation.md
- kaola-workflow/archive/issue-155/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-155/finalization-summary.md
- kaola-workflow/archive/issue-155/mission-ledger.jsonl
- kaola-workflow/archive/issue-155/workflow-state.md
