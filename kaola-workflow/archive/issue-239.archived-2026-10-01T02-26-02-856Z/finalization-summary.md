# Issue 239 — outer-audit correction

## Delivered

The reopened run corrects the four narrow gaps from the outer audit of candidate `2ad984d3`. Delegator inquiry in `templates/kaola-delegator/references/snapshot.md` is self-contained: an idle `send` or a composite `steer --steer-mode interrupt` opens a new turn whose text starts with the selected platform's exact `host_skill_entry`, recovered from the installed host-platforms row (`platforms/<id>.yaml`), including kimi-cli's trailing space and codex's `$` form. Native busy `steer` adds no entry. Grok Bot attestation precedes the operations it guards. An already-verified Host uses the exact `--session` recorded on the snapshot. `templates/kaola-delegator/references/host-brick.md` decides a Host limit from local evidence: explicit exhaustion, a reached rate limit, or a stated window or account limit; an unknown connection, an ambiguous failure, an authentication or account refusal, or a brick does not use that fallback. The existing Host-only ZCode and user branches are unchanged. The prior archive's evidence claims now say the three test-187 failures are pre-existing and their cause is unknown, distinguish the focused checks from the absence of a complete `./scripts/validate.sh` receipt, and compare equivalent file bytes (main Skill plus quota-packages `25523` -> `19370`; the `33715` baseline additionally includes worker-profiles as a conditional extra read). File bytes stay separate from token or cache claims. The live Host snapshot was corrected by the Host. Budgets, manifests, transport, frozen sources, and model or profile policy are unchanged. No release, tag, or install.

## Candidate

`ad380e2b3387f2028e8adc2ff0394e7091c9ff44`, workflow/issue-239.
Worktree: /Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-239
Baseline of this correction: `2ad984d3`. Prior delivery: `9b4012bc`.

## Evidence and acceptance

Host ACCEPTANCE: PASS. The Host verified the diff for the four audit corrections and independently reran `./scripts/render-skills.py --check` (PASS).

Focused checks on the same bytes, before this commit, all exit 0:
- `./scripts/render-skills.py --check` — PASS, budgets OK
- `python3 tests/contract/test-progressive-disclosure.py` — 15 tests OK
- `python3 tests/contract/test-issue-218-preset-ids.py` — 16 tests OK
- `python3 tests/contract/test-generated-skills.py` — PASS
- `tests/contract/test-issue-74-kaola-delegator.py` `test_generated_entry_matrix_and_no_engine_leak` — PASS, 93 assertions

The record for this run is `.cache/final-validation.md` in this folder. The prior archive's `.cache/final-validation.md` remains that earlier run's focused receipt, with its scope line. No complete `./scripts/validate.sh` receipt exists for this correction. The three `NonZCodeHostLifecycle` failures remain the pre-existing observation in `/tmp/187-baseline.log`; their root cause is unknown. Archived mission-ledger done lines were not rewritten.

Protected files, including untracked `docs/harness-acp-compat-2026-10-01.md` and `docs/harness-acp-reverify-2026-10-01.md`, were not staged.

## Known failures or unverified scope

The three test-187 `holder-start-timeout` failures are pre-existing. Their cause is unknown. This correction did not rerun that lifecycle class or `./scripts/validate.sh`. No release, tag, install, or CHANGELOG release section.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- skills/kaola-delegator/references/host-brick.md
- skills/kaola-delegator/references/snapshot.md
- templates/kaola-delegator/references/host-brick.md
- templates/kaola-delegator/references/snapshot.md

## Follow-Up Items

None. This run corrects the same issue's audit record. It does not file the unknown test-187 cause as a new defect.

## Readiness

Host acceptance passed. Ready to archive, merge-sink `workflow/issue-239`, and close issue #239. No release, tag, or install.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-compat-2026-10-01.md
- docs/harness-acp-reverify-2026-10-01.md

## Sink Findings

post_rebase_tests: skipped

archive_collision: kaola-workflow/archive/issue-239/ already existed, so this run is recorded at kaola-workflow/archive/issue-239.archived-2026-10-01T02-26-02-856Z/. The earlier directory stays the prior run. Sink commit 7e8913f3 had replaced that prior run's evidence correction; the following commit restores those two files from ad380e2b. No history rewrite.
