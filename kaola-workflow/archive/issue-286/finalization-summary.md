# Finalization summary — issue #286 (state retire fails closed on unreadable inputs)

## Delivered

`state retire` no longer fails open on an unreadable or unidentified dispatch index,
an unknown closed status, or an unidentified live input. Product change in
`scripts/kaola-dispatch.py` plus its rendered orchestrator Skill copies and the two
$LIVE doc templates; fail-before-fix regression suite; fixture data only in the
existing suites it feeds.

- **G6 — one closed-status vocabulary.** `CLOSED_COVERAGE`
  (`returned`, `failed`, `not-run`) is the one allow-list retire's index read shares
  with its mirror; any other item status — absent, renamed, or unreadable — names an
  open duty (`is not a known closed value`) instead of proving closure.
- **G5 — index identity, fail-closed including undeclared.** An index that is not
  this project's `kaola-dispatch-index/1` — missing or wrong `schema`, missing or
  foreign `repo` — is the typed refusal `index-unidentified` (exit 2, no state bytes
  written; `state check`/`state migrate` share the live refusal path). The index
  mirror applies the same identity check and records a mismatch in
  `index_mirror.error` while the state write stands (I12) and the foreign index
  keeps its bytes.
- **G9 — live identity.** A `--live` input that does not declare
  `kaola-acp-list/1` — no schema or another schema — is the typed refusal
  `live-unidentified` (retire, check, migrate share `live_rows_of`). Real inputs
  are unaffected: `kaola-acp.py list` writes `kaola-acp-list/1`; execute and
  collect write `schema` + `repo` into every index.
- **Docs.** `$LIVE` is named as `{"rows":[...]}` from `list --repo --include-dead`
  (bare `list --repo` omits stopped seats) in
  `templates/orchestrator/references/dispatch-collect.md`; the retire bullet in
  `templates/orchestrator/references/lifecycle-state.md` names the same list form;
  retire `--index`/`--live` argparse help names `kaola-dispatch-index/1` and
  `list --repo --include-dead` rows. Both references stay inside the 8192-byte
  budget (dispatch-collect 8191, lifecycle-state 8181).
- **Suite.** `tests/contract/test-issue-286-retire-input.py` — 10 regressions
  (absent status, unrecognized status, foreign-repo index, wrong-schema index,
  no-schema index, no-repo index, mirror leaves foreign index unchanged, wrong-schema
  live, no-schema live, check identifies live) + 3 guards; registered in
  `scripts/validate.sh` (`python_suites_all` + lane a).
- **Fixture data only** in `tests/contract/test-issue-255-lifecycle-state.py`
  (9 tests + the #281 G7 retire fixture) and
  `tests/contract/test-issue-259-record-contract.py`: hand-written index/live files
  carry the fields their real producers write. No #281 assertion weakened.
- **CHANGELOG.** Unreleased entry under `## Unreleased` (section `Seats: restart
  required` comes from the #278 holder change; the #286 entry notes it is state
  tooling only).

## Candidate

- Host review 1 accepted the repair candidate `ae3f0e5b` (fail-closed on undeclared
  identity; rebase on `60e9e717`), re-ran the suite (13 OK) and confirmed no
  protected path in range. Original fail-safe candidate `d834530f`; review-1
  repair `ae3f0e5b`.
- Final rebase onto newest `origin/main` `9c88c0ef` (#281/#282/#277/#275-slice-1
  fixtures and suite lines, #283/#284/#285 docs) auto-merged with no conflicts.
  Branch tip at publication: `f682a699` (294ff16c original G5/G6/G9 fix →
  9b910b1b review-1 repair → f682a699 the #281 G7 retire fixture's live identity
  line).

## Evidence locations

- Fail-before-fix on main: at `60e9e717` the suite failed 10/10 regressions with
  3/3 guards passing (detached temp checkout, since removed).
- Post-rebase five-suite validate from the candidate worktree, exit 0, 96.4 s wall:
  `./scripts/validate.sh --suite test-issue-286-retire-input.py --suite
  test-issue-255-lifecycle-state.py --suite test-issue-259-record-contract.py
  --suite test-issue-267-rejection-count.py --suite test-issue-244-dispatch.py`
  — counts 286: 13, 255: 131, 259: 63, 267: 29, 244: 79, all OK.
- Render: `./scripts/render-skills.py --write` then `--check` PASS at content stage
  (budgets OK, rendered copies byte-identical to sources); at the committed pin
  stage 162 findings, all the pre-existing stale-release-pin class — main
  `9c88c0ef` baseline plus exactly 2 naming this work's own test files
  (`test-issue-259-record-contract.py`, `test-issue-286-retire-input.py`), zero
  non-pin findings.
- Run folder `.cache/final-validation.md` (verdict pass, bound to this worktree).

## Known failures or unverified scope

- The release pin `3de9f61afbfa` is stale on main and was not edited (pre-existing;
  release activity, out of scope). Pin-stage `render-skills.py --check` exits 1
  with the findings above on main and this branch alike.
- Refusal names `index-unidentified` and `live-unidentified` are new contract
  vocabulary; host accepted both in review 1.
- The other C4 seams (G1–G4, G7, G8) are covered by #281's fixtures; this issue
  covers G5, G6, G9 only.

## Validation

classification: final_validation_stale
green: false
mode: final-validation

recorded validated_candidate_hash "a10ea7e83fc05b64459ab501c64b87427d05eee04713346c7430fd9cfdcf9fc0" != current code-tree hash "6d064a75aeb5876f81a070e27b11146710c40b00287546da479d393a737868c8" — a relevant source/test/test-consumed file changed after the recorded validation; re-run the validation command and re-record final-validation.md with a fresh hash

A relevant source/test/test-consumed file changed after validation — or the record was written from a different checkout than this one. Re-run the validation command, then re-record with `kaola-workflow-validation-runner.js record --project <project> --verdict pass --command "<the validation command you ran>"`, invoked from the working tree you validated (the gate hashes the tree its own shell is in, and a linked worktree and main differ until the branch merges); never hand-patch the hash.

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- scripts/kaola-dispatch.py
- scripts/validate.sh
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/dispatch-collect.md
- skills/kaola-project-runner/references/lifecycle-state.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/references/dispatch-collect.md
- templates/orchestrator/references/lifecycle-state.md
- tests/contract/test-issue-255-lifecycle-state.py
- tests/contract/test-issue-259-record-contract.py
- tests/contract/test-issue-286-retire-input.py

## Follow-Up Items

None filed. No run-discovered defect beyond the issue scope; the review-1 finding
(undeclared identity must not pass) is closed by this candidate.

## Final readiness

Ready: candidate frozen, suites green, evidence recorded, merge sink
(`sink: merge`, issue 286) pending publication and close.

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
- kaola-workflow/archive/issue-286/finalization-summary.md
