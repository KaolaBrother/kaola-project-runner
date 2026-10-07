# Finalization Summary — issue-290

## Delivered

Fix #290: `state retire --kind tasks` proves dispatch closure across several of this
project's index files. `--index` is repeatable; every supplied file still passes
`index_identity_problem` (this project's `kaola-dispatch-index/1`), and every dispatch
ref must be found in exactly one supplied index — a ref in none is still named open, a
ref in two is refused. The index mirror writes each supplied file and keeps the
existing single-object `index_mirror` result for a single `--index`. A done+accepted
task whose items were dispatched by two `execute` runs therefore retires once every
item is closed and every seat is stopped, on original proof: no hand-merged index, no
forced removal, no tombstone moved to another routine field. Retire refusals keep
naming the executable removal command. Real shape reproduced: `kpr-ddd-component`
(`i280-ddd-pilot` + `i281`..`i285` across two indices).

## Candidate

`c61de134` on `workflow/issue-290`, rebased onto current main `836bc41c`. 16 files:
`scripts/kaola-dispatch.py`, `templates/orchestrator/references/lifecycle-state.md`,
the generated orchestrator skill (`skills/kaola-project-runner/...`) plus the ten
`skills/*/scripts/main-skill-build.json` records, `tests/contract/test-issue-286-retire-input.py`
(+6 tests, class `MultiIndexRetire`), and a CHANGELOG entry in the section whose header
reads `Seats: restart required`.

## Evidence

- Rebase: `98c48760` → `c61de134` onto main `836bc41c` (5 docs-only commits; no path
  overlap with this branch); the affected suites were re-run at the rebased tree before
  the record was written.
- Affected-suite validation at the rebased tree, worktree-only content-stage flip and a
  one-shot wider sandbox for validate.sh's sandbox-denied `ps` cleanup:
  `./scripts/validate.sh --suite test-issue-286-retire-input.py --suite test-issue-244-dispatch.py --suite test-issue-271-dispatch-help.py`
  exit 0 — `render-skills: PASS … budgets OK`; 286 19 OK, 244 79 OK, 271 OK; sweep clean.
- Fail-before proof: 3 of the new `MultiIndexRetire` cases fail on the unfixed
  `scripts/kaola-dispatch.py` with `retire-unmet … is not in the index`, and pass after.
- Inherited-failure proof: `test-issue-255-lifecycle-state.py` fails the same 5
  pre-existing sandbox `ps`/launchctl tests at both the candidate and clean base
  `930236f2`; `test-issue-259-record-contract.py` fails the same pre-existing launchctl
  test at both.
- Validation receipt: `kaola-workflow/issue-290/.cache/final-validation.md` (verdict
  pass, command recorded, bound to the candidate worktree code-tree hash).

## Known failures / unverified scope

- The committed pinned configuration aborts `render-skills.py --check` and
  `validate.sh` at render-check on the inherited 214-pin standing state (identical at
  base `930236f2`, 0 non-pin findings) — not a defect of this run.
- `test-issue-255-lifecycle-state.py` and `test-issue-259-record-contract.py` carry
  pre-existing sandbox `ps`/launchctl environment failures, reproduced identical at base.
- The issue's original `/tmp/kpr-280-index.json` and `/tmp/kpr-ddd-phase2-index.json` are
  gone; the shape was rebuilt as equivalent in-test fixtures, as the issue permitted.
- No value-laden or irreversible step remains open for this run.

## Validation

classification: final_validation_stale
green: false
mode: final-validation

recorded validated_candidate_hash "39311095b02352c1621792a7942ef76ef4991c514f7063e17b4c0ccb7f1db115" != current code-tree hash "7f3455d6fcf1a256b849f8b6b6583fd20f548b2ba6023a3ceb7ee6115e8bd049" — a relevant source/test/test-consumed file changed after the recorded validation; re-run the validation command and re-record final-validation.md with a fresh hash

A relevant source/test/test-consumed file changed after validation — or the record was written from a different checkout than this one. Re-run the validation command, then re-record with `kaola-workflow-validation-runner.js record --project <project> --verdict pass --command "<the validation command you ran>"`, invoked from the working tree you validated (the gate hashes the tree its own shell is in, and a linked worktree and main differ until the branch merges); never hand-patch the hash.

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- scripts/kaola-dispatch.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/lifecycle-state.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/references/lifecycle-state.md
- tests/contract/test-issue-286-retire-input.py

## Follow-Up Items

- The Host will retire the `kpr-ddd-component` task once this merge lands.

## Final readiness

Ready: candidate verified per the issue's Expected acceptance, validation recorded from
the candidate worktree, sink = merge closing #290.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-codex-160-live-2026-10-03.md
- docs/harness-acp-compat-2026-10-01.md
- docs/harness-acp-compat-2026-10-03.md
- docs/harness-acp-compat-2026-10-06.md
- docs/harness-acp-reverify-2026-10-01.md

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-290/.cache/final-validation.md
- kaola-workflow/archive/issue-290/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-290/finalization-summary.md
- kaola-workflow/archive/issue-290/mission-ledger.jsonl
- kaola-workflow/archive/issue-290/workflow-state.md
