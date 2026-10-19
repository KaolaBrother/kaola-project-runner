# Finalization Summary — issue-357

## Delivered

Issue #357 (bookkeeping 2): the backstop sweep removes a merged local branch of a closed issue, and it only reports the residues that must not be deleted.

- Rule B1 removes a local `workflow/issue-N` branch once its issue is CLOSED, no surviving worktree checks it out, no verified session for that issue is live, and it is merged. A tip that is an ancestor of the remote head uses `git branch -d`. An exact merged-PR head uses `git branch -D`. Remote branches are never deleted. The candidate carries a `git branch` restore hint.
- Report-only rules R1–R3 list, in the receipt's `report` list only, active Kaola-Workflow folders of closed issues, `.kaola/` entries that are not Project Runner artifacts, and heartbeat-prompt backups. They never enter candidates, kept, alerts, `last_sweep`, or `maintenance`.
- A node `--apply --batch` re-verifies branch plan ids. A reopened issue is `no-longer-candidate`.
- Rebased onto `4c592de8` after #353, #354, and #355. The sweep patch body matches the accepted delivery `88c916f9`. `CHANGELOG.md` keeps the #353, #354, #355, and #357 Unreleased bullets, and the section line stays `Seats: restart required`. Generated `main-skill-build.json` hashes were regenerated with `./scripts/render-skills.py --write`.

## Candidate

Branch `workflow/issue-357`, parent `4c592de8a11215e3484ef43140823673d7dd018b`.

- `072012f6dc195857c2dd12089355986e965f343b` — `Sweep merged closed-issue branches and report non-removable residues (#357)`

Acceptance candidate: `072012f6`. Worktree clean. This finalize adds no implementation commit.

Host acceptance: ACCEPTED. The acceptance of `88c916f9` still covers this candidate because the patch body is the same.

The operator diff of `4c592de8..072012f6` is empty (`scripts/kaola-acp-holder.py`, `scripts/kaola-zcode-acp.py`, `scripts/kaola-quota.py`, `scripts/kaola-record-contract.py`, `scripts/adapters`, `platforms`, `scripts/kaola-acp-paths.py`). `scripts/kaola-dispatch.py` is outside that set. The `## Unreleased` section line stays `Seats: restart required` because #353 changes `scripts/kaola-acp-holder.py`.

## Evidence

- Fail-on-main, on `c9af2517` with only the new test file: `Ran 33 tests` / `FAILED (failures=5, errors=3)`. After the change: `Ran 33 tests` / `OK`.
- Six-situation fixture `test_b1_six_cases`: merge-commit, squash, unmerged, checked out by a worktree, reopened after the scan, and an open issue. Two dry-runs match. Refs, `ls-remote`, and the state file bytes stay unchanged. `GIT_TRACE` shows `branch -d workflow/issue-21` and `branch -D workflow/issue-22`, and no push. Restore by SHA succeeds.
- Squash recoverability, measured read-only in this repository: PR #134 (`workflow/issue-133`, merged) has no remote branch, and `refs/pull/134/head` = `394caf77` = that PR's `headRefOid`, fetchable (`cat-file -t` → commit). A branch deleted by exact SHA can be restored with `git fetch origin pull/<PR>/head` and `git branch workflow/issue-N <sha>`. An ancestor SHA is already reachable from `origin/<default>`.
- Focused suites after the rebase, on `072012f6`, `KAOLA_LAUNCH_BACKEND=direct`, `KAOLA_ZCODE_*` cleared: `test-issue-348-backstop-sweep.py` Ran 33 tests OK; `test-progressive-disclosure.py` Ran 15 tests OK; `test-generated-skills.py` generated Skill acceptance PASS; `test-issue-255-lifecycle-state.py` Ran 142 tests OK. `./scripts/render-skills.py --write` and `--check` PASS.
- Host full inventory `./scripts/validate.sh` (no `--suite`) in the worktree at `072012f6`, direct backend, environment cleared: exit 0, 1453.81 s, no flake. This candidate's record has this one timed full inventory. Recorded in `.cache/final-validation.md`.
- Evidence comments: issuecomment-6260578840, issuecomment-6261720200.

## Known failures and unverified scope

- No known product failure on `072012f6`.
- No release, tag, or install in this finalize.
- Counts and sizes in other projects stay unreproduced. This issue did not open those trees.
- Four Owner questions stay on issuecomment-6260578840: unmerged branches listed in `sweep-kept`, `.kaola/run/` treated as a Project Runner artifact, large directories listed but not deleted, and `git branch -d` left as `remove-failed` when it refuses. They were not re-decided here.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- README.md
- docs/api.md
- scripts/kaola-dispatch.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/doc-maintenance.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/references/doc-maintenance.md
- tests/contract/test-issue-348-backstop-sweep.py

## Follow-Up Items

- None filed.
- No release, tag, or install in this finalize.

## Readiness

Host accepted `072012f6`. The Host full-gate result is reused. Merge sink into local main after #353, #354, and #355, push to origin, close issue #357, release the claim label, archive.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-357/.cache/final-validation.md
- kaola-workflow/archive/issue-357/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-357/finalization-summary.md
- kaola-workflow/archive/issue-357/mission-ledger.jsonl
- kaola-workflow/archive/issue-357/workflow-state.md
