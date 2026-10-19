# Finalization Summary — issue-355

## Delivered

Issue #355 (bookkeeping 1C): Delegator state keeps only current facts. An unknown top-level key has a named removal, view shows open watch rows, and a handled watch row is set to null in the same update.

- `delegator update --writer delegator --expect-revision REV --set '{"KEY":null}'` removes an unknown top-level key such as `handled_wakes`. Still-valid duties in that value become normal `watch` rows in the same update. The Delegator judges which duties are still valid.
- The refusal names the collection, the id, the revision, and that command. A repeat null of a key that is already absent does not write. A stale `--expect-revision` refuses and says to re-read the file.
- `delegator view` computes the non-terminal watch count, the earliest `at`, and the `{"watch":{"ID":null}}` clear command, and it writes nothing.
- A handled watch row is set to null in the same update that handles it. `handled_*` bookkeeping is not stored in another field. Only the Delegator writes the delegator file.
- Rebased onto `7e255f0b` after #353 and #354. `scripts/kaola-dispatch.py` auto-merged. `CHANGELOG.md` keeps the #353, #354, and #355 Unreleased bullets, and the section line stays `Seats: restart required`. Generated `main-skill-build.json` hashes were regenerated with `./scripts/render-skills.py --write`.

## Candidate

Branch `workflow/issue-355`, parent `7e255f0b9692bce408eccb80ce5fc5614e3485ca`.

- `974c32cda1770a59e7a476c08a230c480d0a2505` — `Name the removal for unknown delegator keys (#355)`

Acceptance candidate: `974c32cd`. Worktree clean. This finalize adds no implementation commit.

Host acceptance: ACCEPTED.

The operator diff of `7e255f0b..974c32cd` is empty (`scripts/kaola-acp-holder.py`, `scripts/kaola-zcode-acp.py`, `scripts/kaola-quota.py`, `scripts/kaola-record-contract.py`, `scripts/adapters`, `platforms`, `scripts/kaola-acp-paths.py`). `scripts/kaola-dispatch.py` and `templates/kaola-delegator/` are outside that set. The `## Unreleased` section line stays `Seats: restart required` because #353 changes `scripts/kaola-acp-holder.py`.

## Evidence

- Fail-on-main: on `b35165ff`, before the dispatch edit, the new test failed with `non-terminal watch count excludes adopted ({})`.
- Focused suites after the rebase, on the tree committed as `974c32cd`: `./scripts/validate.sh --suite test-issue-74-kaola-delegator.py --suite test-issue-302-delegator-wake-gate.py --suite test-issue-255-lifecycle-state.py` exited 0 (wall 194.452 s). issue-74: `231 assertions, 0 failed tests` (elapsed 12.502 s). issue-255: `Ran 142 tests in 105.806s` OK (elapsed 105.989 s). issue-302: `Ran 38 tests in 181.149s` OK (elapsed 181.238 s). `render-skills` PASS, content stage unpinned. `kaola-grok-bot-verify` PASS.
- Host full inventory `./scripts/validate.sh` (no `--suite`) in the worktree at `974c32cd`, direct backend, environment cleared: exit 0, 1358.32 s, no flake. This candidate's record has this one timed full inventory. Recorded in `.cache/final-validation.md`.
- Evidence comments: issuecomment-6259772811, issuecomment-6260975705.

## Known failures and unverified scope

- No known product failure on `974c32cd`.
- No release, tag, or install in this finalize.
- The live `.kaola/delegator-heartbeat.json` stayed revision 38 and was not edited.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- scripts/kaola-dispatch.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-delegator/references/inquiry-report.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/kaola-delegator/references/inquiry-report.md
- tests/contract/test-issue-74-kaola-delegator.py

## Follow-Up Items

- None filed.
- No release, tag, or install in this finalize.

## Readiness

Host accepted `974c32cd`. The Host full-gate result is reused. Merge sink into local main after #353 and #354, push to origin, close issue #355, release the claim label, archive.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-355/.cache/final-validation.md
- kaola-workflow/archive/issue-355/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-355/finalization-summary.md
- kaola-workflow/archive/issue-355/mission-ledger.jsonl
- kaola-workflow/archive/issue-355/workflow-state.md
