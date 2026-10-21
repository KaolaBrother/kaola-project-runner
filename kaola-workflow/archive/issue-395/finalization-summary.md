# Finalization Summary — Issue #395

## Delivered

`state retire` now closes the vrpai legacy-alert shape: an `alerts` row that
predates record revisions (`rev` absent or unusable), whose `inputs` is an
empty object (structurally resolved), can leave with explicit `--expect-rev 0`
and non-empty `--evidence` instead of first requiring `state migrate --write`.

The direct path is deliberately narrow: only `kind == alerts`, no usable
record revision, `inputs == {}`, an explicit `--expect-rev 0`, and non-empty
evidence after stripping. The row is removed without assigning a revision and
the supplied evidence is carried in the operation receipt. Versioned rows at
`--expect-rev 0` still conflict; `update` and the returned-input settle still
refuse a versionless row; missing, null, non-empty, or non-dict `inputs` still
take the migrate route; and a missing row still refuses `record-missing`.
Later retire gates such as `retire-unmet` remain in place.

`state check` emits the direct command for this shape, and
`versionless_recovery` plus the `record-versionless` recovery route now name
both exits (direct retire for the resolved empty-inputs alert, migrate for
everything else). A non-object row now returns a JSON `state-unreadable`
refusal instead of an `AttributeError` traceback.

`tests/contract/test-issue-395-alert-direct-retire.py` covers the direct
success, unresolved and non-dict inputs, absent inputs, versioned conflict,
update and returned-input settle, check command execution, the non-object
guard, and blank/nonzero direct-only negatives. `test-issue-362-versionless-retire.py`
now splits direct retire from migration, and its non-alert decision fixture
carries the same empty inputs and revision/evidence state as an eligible alert
so the kind dimension is isolated. Both suites are registered in
`scripts/validate.sh`; generated Skill copies were refreshed from source.
`docs/api.md`, `docs/conventions.md`, and `CHANGELOG.md` record the behavior.
No tag, release, or install was performed.

## Candidate

Branch `workflow/issue-395` at `4af8bfda0e29017faa64f4e5924e257e0ed445fb`,
based on main `610c5038343542821b282173bf09b597ddb97ecd`. The implementation
commit is `8a798036c2a93017eb504574cf6873c5027c22ca`; `4af8bfda` is the
test-only acceptance-repair commit. The tip was accepted by the Host after
independent review.

## Evidence

- Host acceptance: verdict `accepted` at `4af8bfda`; independent review
  confirmed the five-condition direct path, input variants, versioned
  conflict, update/settle refusal, `record-missing`, evidence receipt,
  `isinstance` guard, baseline red, focused suites, render, and documentation.
- `tests/contract/test-issue-395-alert-direct-retire.py` — 11 tests, 2 skips
  reserved for #397 scope (v1 `body.alerts` and large-carrier retirement).
- `tests/contract/test-issue-362-versionless-retire.py` — 4 tests, including
  the decision+`inputs: {}` kind-isolation guard.
- Focused `./scripts/validate.sh --suite test-issue-395-alert-direct-retire
  --suite test-issue-362-versionless-retire` at clean `4af8bfda`: 15 tests OK
  (11 with 2 skips, plus 4). Earlier focused runs at `8a798036` also passed
  `test-issue-286-retire-input.py`, `test-issue-354-state-bloat.py`,
  `test-issue-372-stale-collect-retire.py`, and
  `test-issue-309-recovery-routes.py`; the test-only repair changed no
  implementation, generated copies, or those suites' fixtures.
- Baseline `610c5038`: the new suite reports 4 failures and 2 skips; the
  direct-shape reproduction refuses `record-versionless`.
- Mutation verification on the accepted tests: removing the alerts-only kind
  guard turns the #362 decision case red; removing the evidence strip guard
  turns both blank-evidence cases red; relaxing the exact-zero guard turns the
  nonzero `--expect-rev 1` case red. The mutation script was restored and the
  worktree implementation was unchanged.
- `render-skills.py --check` PASS at `4af8bfda`.
- `kaola-workflow/issue-395/.cache/final-validation.md` records the pass at
  candidate hash `76aeffb232a3b42ff6438fb21c7e86b43e93180e5b5148ce300875a8afa1f049`.

## Known failures or unverified scope

- The full `scripts/validate.sh` inventory was not run by this run; the
  focused suites, render check, Host acceptance, and independent review cover
  the changed paths.
- #397 remains open for v1 `body.alerts` mapping and large-carrier retirement
  (`carrier-limit` loop); the two skips in the new suite name that boundary.
- The `templates/orchestrator/references/lifecycle-state.md` reference was not
  expanded; its byte budget leaves 9 B of headroom, and the branch is stated
  in `docs/api.md` plus the `record-versionless` route text.

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
- scripts/kaola-recovery-routes.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- tests/contract/test-issue-362-versionless-retire.py
- tests/contract/test-issue-395-alert-direct-retire.py

## Follow-Up Items

- #397 is the existing open follow-up for v1 `body.alerts` mapping and a large
  carrier without a proving holder. No new issue was filed by this run.
- The generated Skill reference remains at its existing byte budget; keep the
  API and route text as the executable guidance until a budgeted reference
  update is scheduled.

Readiness: accepted candidate at `4af8bfda`, focused suites and renderer
green, ready to merge, archive, and close #395.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-395/.cache/final-validation.md
- kaola-workflow/archive/issue-395/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-395/finalization-summary.md
- kaola-workflow/archive/issue-395/mission-ledger.jsonl
- kaola-workflow/archive/issue-395/workflow-state.md
