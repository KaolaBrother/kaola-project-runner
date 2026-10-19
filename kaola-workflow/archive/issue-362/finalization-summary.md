# Finalization summary — issue-362

## Delivered

`state retire`/`update`/input-settle can now reach records written before
record revisions. Such a record carries no usable `rev`, so no
`--expect-rev` value could name it: retire answered `expect-rev-required`
or `conflict` ("at rev None"), and `state check` emitted an unparseable
`--expect-rev None` command. Resolved legacy alerts (the vrpai
`exclusion-breach-codex-default-i1687`/`i1779` rows) were stuck in the
file and in the bounded Host view.

- `scripts/kaola-record-contract.py`: `cleanup_current` assigns `rev 1`
  to each pre-revision record, listed as `<kind>.<id>.rev assigned 1
  (pre-revision record)` in the migrate plan's `removed`.
- `scripts/kaola-dispatch.py`: `record_versionless` guard; `update`,
  `retire`, and `settle_inputs` refuse `record-versionless` with a
  `recovery` naming the read-only migrate plan then `--write`;
  `state check` emits that plan as the row's `command` instead of
  `--expect-rev None`; `settle_recovery`/`update_hint_command` likewise.
- `scripts/kaola-recovery-routes.py`: `route` rows for
  `record-versionless` and (a gap left by #365)
  `missing-host-holder-instance-id`.
- `tests/contract/test-issue-362-versionless-retire.py`: 3 cases —
  migrate-then-retire regression, unresolved-versionless stays refused,
  versioned conflict semantics unchanged. Fails on the pre-fix base
  (2/3); passes on the candidate.
- Docs: `docs/api.md` migrate entry, `docs/conventions.md` migration
  `removed` list, `templates/orchestrator/references/lifecycle-state.md`
  check bullet; `CHANGELOG.md` Unreleased entry
  (`Seats: restart required` — `kaola-record-contract.py` is in the
  operator restart set); generated `skills/`/`hosts/` re-rendered.

## Candidate

`56245739` on `workflow/issue-362`, rebased onto main `153409b8`
(includes #364, #365, #367, #363). Prior accepted candidate `b6819a1b`
was content-approved; rebase only re-based it.

## Evidence

- Reproduction (pre-fix): `state retire` -> `expect-rev-required`;
  `--expect-rev 0` -> `conflict` "at rev None"; `state check` command
  contained literal `--expect-rev None` (argparse `invalid int value`).
- Host view shrinks after migrate+retire (fixture: 871 B -> 415 B).
- `.cache/final-validation.md`: `verdict: pass`, exact command recorded.

## Known failures / unverified scope

- Not exercised on the real vrpai state file (not on this machine);
  fixture replicates the described shape (schema /2, resolved
  `inputs: {}`, no `rev`, ~2.5 KB rows).
- Full inventory not run here — Host runs the whole suite at release.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- docs/conventions.md
- scripts/kaola-dispatch.py
- scripts/kaola-record-contract.py
- scripts/kaola-recovery-routes.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-record-contract.py
- skills/antigravity-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/kaola-record-contract.py
- skills/claude-code-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-record-contract.py
- skills/codex-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-record-contract.py
- skills/devin-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-record-contract.py
- skills/droid-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-record-contract.py
- skills/dsh-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-record-contract.py
- skills/grok-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/lifecycle-state.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kaola-project-runner/scripts/kaola-record-contract.py
- skills/kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/opencode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/zcode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/references/lifecycle-state.md
- tests/contract/test-issue-362-versionless-retire.py

## Follow-Up Items

- None filed. The `missing-host-holder-instance-id` route row is a gap
  #365 left on main; this branch already repairs it in
  `scripts/kaola-recovery-routes.py`, so no separate issue was opened.

## Readiness

Accepted by Host (content review + suite OK + render PASS). Ready for
merge sink: local main merge, push, close #362, archive, cleanup.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-362/.cache/final-validation.md
- kaola-workflow/archive/issue-362/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-362/finalization-summary.md
- kaola-workflow/archive/issue-362/mission-ledger.jsonl
- kaola-workflow/archive/issue-362/workflow-state.md
