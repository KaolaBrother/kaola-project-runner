# Issue 242 — Clarify lifecycle guidance placement without changing established rules

## Delivered

Four placements in the generated Project Runner Skill, from `templates/orchestrator/SKILL.md.tmpl` only, then regenerated. Established rule words stay.

1. The QA read sentence now sits in step 2 immediately after the idle-before-stop sentence, and ends with a period. It still covers planning, assigning, and judging, and still reuses the current in-context reference.
2. Step 3 ends `you pick when aggregate QA/doc checks run; unrun ones stay pending duties.`
3. The fresh-start / same-assignment paragraph sits in step 5 immediately after `Idle is not keep-alive or completion.`
4. A paragraph break precedes `A Host that ended its turn...`, and that paragraph stays in step 5 with its original wording. The step 5 heading is `Reclaim seats and report`.

No release, tag, install, or CHANGELOG release section. Byte ceilings were not raised. Because this checkout was the v0.6.17 pin, `templates/grok-bot/accepted-revision.json` returned to the content stage so the renderer could write; generated `hosts/grok-bot/` is the unpinned content-stage bridge and is not saveable.

## Candidate

fb9ea3f03cd355524e4b2d898ab01a6e8d9184c6, workflow/issue-242.
Worktree: /Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-242
Baseline: e248004d. Diff: 16 files, +60/−64.

## Evidence and acceptance

Host ACCEPTANCE: PASS. The Host verified all four edits on the generated `skills/kaola-project-runner/SKILL.md`: QA-read sentence at line 174 immediately after the idle-before-stop sentence (period ending; still covers planning, assigning, and judging, with the in-context reuse clause); step-3 tail joined at line 205 (`run; unrun ones stay pending duties.`); fresh-start / same-assignment paragraph directly after `Idle is not keep-alive or completion.` in step 5; paragraph break before `A Host that ended its turn...` with original wording; heading `Reclaim seats and report` at line 215.

Host independent word-token multiset diff of the template against HEAD: exactly `{Reclaim:+1, Release:-1, seats:+1}`, the heading change, plus the two punctuation joins, matching the reviewed draft.

Host independent byte check, matching this candidate:
- Host entry `skills/kaola-project-runner/SKILL.md` 16527 → 16539 B (+12; ceiling 17408)
- Template `templates/orchestrator/SKILL.md.tmpl` 15690 → 15702 B (+12)
- References and Delegator hashes unchanged
- Ceiling 17408 untouched

Host bounded QA VERDICT: PASS. QA is read before planning, assignment, and judging at its first point of need. Worker reclamation and Host/mandate continuity are separate paragraphs. Fresh-context / same-assignment recovery sits with reclamation. The #241 dispatch-choice sentence, the #208 owned-duty exception, same-beat stop, and acceptance-before-finalize remain verbatim. Conditional references stay conditional. No new rules or machinery.

Worker affected-check battery on these same bytes, all exit 0, run in this worktree before the commit (the commit did not change those bytes): `./scripts/render-skills.py --check` PASS (content stage, unpinned, not saveable; budgets OK; bridge 2555 B); progressive-disclosure (15 OK); test-issue-41-orchestrator (23 OK); test-generated-skills PASS; test-issue-118-seat-cap (18 OK); test-issue-119-host-entry (11/11, 164 checks); test-issue-65-host-contract (13 OK); test-issue-68-heartbeat-snapshot (8 OK); test-issue-72-session-naming (16 OK); Issue49PinModel.test_project_stage_is_consistent_with_its_own_checkout OK.

`run-chains --project issue-242` from this worktree: exit 1, `chains_config_missing` — this repo has no `package.json` `test:kaola-workflow:*` scripts. Consumer finalize evidence is `.cache/final-validation.md` (`verdict: pass`, command the focused battery above, hash `adbc3a065f67d304abd8601f166e7e232ccf4da58e4ce96a95b82415827938e3`). That receipt is not a `./scripts/validate.sh` receipt.

Protected files, including untracked `docs/harness-acp-compat-2026-10-01.md` and `docs/harness-acp-reverify-2026-10-01.md`, were not staged or deleted.

## Known failures or unverified scope

No failure on this candidate. No release, tag, install, or CHANGELOG release section. `main-skill-build.json` hashes changed with the Host entry; this run did not reinstall. Repository-candidate validation does not claim the installed release changed. The design-run retention of an already-delivered helper was an execution observation; this placement change does not alter Host behavior.

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

Ready to merge and close issue #242.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-compat-2026-10-01.md
- docs/harness-acp-reverify-2026-10-01.md

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-242/.cache/final-validation.md
- kaola-workflow/archive/issue-242/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-242/finalization-summary.md
- kaola-workflow/archive/issue-242/mission-ledger.jsonl
- kaola-workflow/archive/issue-242/workflow-state.md
