# Issue #89 — Finalization Summary

No-code closeout. Branch `workflow/issue-89` at `5dd18da` (= origin/main at claim and at
close). Outer ACCEPT of mission 6: OpenCode `acp_verified_versions cli=1.18.29` is a real
live ACP PASS; the existing contract has no last-live obligation; the issue's stale-defect
hypothesis is falsified. No production files were changed. No release.

## Delivered

Evidence correction, not a restamp.

- `platforms/opencode.yaml` `acp_verified_versions: "cli=1.18.29;protocol=1"` was written in
  `ed61666` after live scenarios 1/3/4/7. Primary receipts:
  `docs/acp-live-verification-2026-09-11.md` and
  `kaola-workflow/archive/bundle-18-19-20-21/evidence/opencode-preflight.json`
  (`agent_info.version=1.18.29`, `protocol_version=1`).
- Issue #24 later measured skip-all on that same 1.18.29 and did not introduce the stamp.
- Design `docs/runner-v2-dual-transport-design.md` §7.5 records "已验证的 CLI 版本" as a
  fact. Runtime copies the string onto `bridge.verified_versions`. There is no implemented
  `verified_version_match` gate and no test that the stamp equal the most recent live CLI.
- Later live does not obligate a restamp. Kimi stays `cli=0.41.0` after #65 live-passed
  `agent_info.version=2.0.0`. OpenCode #65 live-passed 1.18.31; #88 kept `cli=1.18.29` and
  recorded 1.18.31 only as composite-interrupt evidence in `steering_summary`.
- A last-live RED draft was written, proven RED on `5dd18da` (10 tests, 7 FAIL / 3 PASS),
  then withdrawn uncommitted after outer correction. Log:
  `evidence/red-5dd18da.log`. The test file and `scripts/validate.sh` registration are gone
  from the worktree; they were never committed.

## Files Changed

None in the product tree. `git diff --stat origin/main` on `workflow/issue-89` is empty.
The withdrawn uncommitted draft is not in HEAD.

Run records only (archived by finalize/sink): this summary, mission-list, workflow-state,
doc-docking, the RED log, and the issue comment.

## Test Coverage

No new product test. The withdrawn RED draft is run history, not coverage.

## Validation

Recorded from the candidate worktree after the draft was withdrawn
(`.cache/final-validation.md`):

- command: `git diff --stat origin/main && test -z "$(git status --porcelain)" && ./scripts/render-skills.py --check`
- result: empty diff vs `origin/main`, clean porcelain, `render-skills.py --check` PASS (budgets OK), exit 0
- `validated_candidate_hash`: `9191c9dcbca0f78eb4f4146141e7a7cec410aa21cc58811f22baf5537a1ffcc9` bound to worktree `.kw/worktrees/issue-89` at `5dd18da`
- `./scripts/kaola-workflow-run-chains.js --project issue-89` → `chains_config_missing` (expected consumer path; finalize gates on the recorded file, not npm chains)

Issue correction comment posted before close:
https://github.com/KaolaBrother/kaola-project-runner/issues/89#issuecomment-5736146052

## Changed Paths

(none vs origin/main; finalize transaction will restamp this section)

## Documentation Docking

`.cache/doc-docking.md` — **DOCKED**. No public-behavior change, so README, CHANGELOG,
docs/api.md, conventions, the 2026-09-11 live verification, the dual-transport design, and
the OpenCode manifest are no-impact. The dated 1.18.29 live record is left as history.

## Follow-Up Items

None filed. The correction lands as a comment on #89, not as a new issue.

## Readiness

Ready to close: outer ACCEPT of the no-product-change verdict; worktree clean and
identical to origin/main; RED draft withdrawn; RED log retained; documentation docked.
Issue comment before close. Merge-sink archives the run records only. No release.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-89/.cache/doc-docking.md
- kaola-workflow/archive/issue-89/.cache/final-validation.md
- kaola-workflow/archive/issue-89/.cache/mirror-digest.json
- kaola-workflow/archive/issue-89/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-89/evidence/issue-comment.md
- kaola-workflow/archive/issue-89/evidence/withdrawn-red-draft.md
- kaola-workflow/archive/issue-89/finalization-summary.md
- kaola-workflow/archive/issue-89/mission-list.md
- kaola-workflow/archive/issue-89/workflow-state.md
