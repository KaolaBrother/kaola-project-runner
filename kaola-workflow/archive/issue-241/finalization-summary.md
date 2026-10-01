# Issue 241 — Ground new worker selection in current profiles at the dispatch step

## Delivered

Decide and dispatch now gives each clear task to a suitable authorized worker as a new session, chosen from the current heartbeat authorization and rows by owner direction, class responsibility, profile/task fit and capacity. Past dispatch or success informs that choice and does not replace it. Split or parallelize when independent parts gain real time or coverage. The count stays a ceiling; never invent work or expand authorization; at the hard cap, stop one seat before starting any new one.

The always-loaded Authorization duplicate is removed. The delegation principle, Class grants, the Selected-platform current-heartbeat eligibility pointer, and the intake or grant-change catalog-row read trigger remain. Worker-profiles Choosing and the QA Worker preference are unchanged.

No release, tag, install, or CHANGELOG release section. Byte ceilings were not raised. Because this checkout was the v0.6.16 pin, `templates/grok-bot/accepted-revision.json` returned to the content stage so the renderer could write; generated `hosts/grok-bot/` is the unpinned content-stage bridge and is not saveable.

## Candidate

a4b2c3b9db742d401ce20e26e8b93e70ea1b7424, workflow/issue-241.
Worktree: /Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-241
Baseline: e8676910. Diff: 17 files, +53/−54.

## Evidence and acceptance

Host ACCEPTANCE: PASS. The Host verified both edits on the actual diff: the consensus sentence at `SKILL.md:173` with the ceiling, never-invent, and stop-before-start remainder intact; the Authorization duplicate removed (0 occurrences) with the delegation principle, Selected-platform pointer, and intake catalog-row trigger preserved; worker-profiles Choosing and QA preference untouched.

Host independent byte check, matching this candidate:
- Host entry `skills/kaola-project-runner/SKILL.md` 16466 → 16527 B (+61; ceiling 17408; headroom 881)
- `references/heartbeat-skeleton.md` 7866 B (+0)
- `references/worker-profiles.md` 8074 B (+0)
- `references/qa-evidence.md` 6846 B (+0)

Host bounded QA VERDICT: PASS. The rendered decision-point text is consistent with worker-profiles Choosing and the Selected-platform eligibility pointer; the always-loaded entry no longer duplicates that rule; continuity, repair, and finalize ownership are untouched; no new mechanism.

Worker affected-check battery on these same bytes, all green: `./scripts/render-skills.py --check` PASS (content stage, unpinned, not saveable; budgets OK); progressive-disclosure (15 OK); test-issue-41-orchestrator (23 OK); test-generated-skills PASS; test-issue-218-preset-ids (16 OK); test-issue-118-seat-cap (18 OK); test-issue-119-host-entry (11/11, 164 checks); test-issue-65-host-contract (13 OK); test-issue-68-heartbeat-snapshot (8 OK); test-issue-72-session-naming (16 OK); Issue49PinModel.test_project_stage_is_consistent_with_its_own_checkout OK.

Host full validation, run inside this worktree: `./scripts/validate.sh` exit 0. Receipt log `/tmp/kpr-241-full-validate.log` (761 lines): 12× `validate-skill: PASS`, 0 FAILED, `kaola-grok-bot-verify: PASS` on `hosts/grok-bot` (2555 B, stage content), residuals empty (`residual_pids: []`).

`run-chains --project issue-241` from this worktree: exit 1, `chains_config_missing` — this repo has no `package.json` `test:kaola-workflow:*` scripts. Consumer finalize evidence is `.cache/final-validation.md` (`verdict: pass`, command `./scripts/validate.sh`, hash `3281508f281d3d6838897f7ddfcba27ce1598e1cc695c7ae414aedf1f1f79855`).

Protected files, including untracked `docs/harness-acp-compat-2026-10-01.md` and `docs/harness-acp-reverify-2026-10-01.md`, were not staged or deleted.

## Known failures or unverified scope

No failure on this candidate. No release, tag, install, or CHANGELOG release section. `main-skill-build.json` hashes changed with the Host entry; this run did not reinstall. Repository-candidate validation does not claim the installed release changed.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- scripts/render-skills.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/SKILL.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/grok-bot/accepted-revision.json
- templates/orchestrator/SKILL.md.tmpl

## Follow-Up Items

None. No run-discovered defect was filed.

## Readiness

Ready to merge and close issue #241.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-compat-2026-10-01.md
- docs/harness-acp-reverify-2026-10-01.md

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-241/.cache/final-validation.md
- kaola-workflow/archive/issue-241/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-241/finalization-summary.md
- kaola-workflow/archive/issue-241/mission-ledger.jsonl
- kaola-workflow/archive/issue-241/workflow-state.md
