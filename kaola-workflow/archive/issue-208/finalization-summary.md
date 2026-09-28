# Finalization Summary — Issue #208

## Delivered

Consolidated repeated prompt guidance and retired conflicting lifecycle instructions in candidate `f08da0b5facb3980adf80061cb1a7f58acc43dd6` (base `4206eafb`, no re-sync needed). Host accepted the candidate after independently verifying the six design items in the diff.

Issue walk:
1. Heartbeat repeats static policy — `heartbeat-skeleton.txt` keeps only project identity/authorization, task and worker locators, frontier, open decisions/close-out, recovery pointers, plus the existing write-back subtraction and `body` carrier rules; stable rules live once in the main Skill loaded every beat. No new schema/table/registry. Rendered 8191 → 3735 B.
2. Acceptance/stop conflict — main Skill step 5 states once: acceptance authorizes pending finalize; an accepted seat keeps only the finalize/cleanup duties it owns; exact-stop once it owns none (done or handed off) or is abandoned. Stop-on-completed-assignment, same-assignment repair and "Idle is not keep-alive" preserved; `zcode-host-dispatch` and `qa-evidence` point to step 5.
3. Unsupported lifecycle inference — `issue-dispatch.md` no longer infers archive, finalize-in-progress, waiting or "forgotten archive" from a missing ledger or terminal missions; lifecycle is judged from Workflow/forge records and the responsible owner. No replacement state machine.
4. Startup/recovery layering — `host-startup` hand-read ban is ZCode-scoped, preserving the Codex compact hook reread; probe narratives/issue attribution removed from `host-entry-matrix` and Delegator `host-platforms` (history already in `docs/host-entry-evidence.md`); owner-acceptance on explicit installed-Skill read kept.
5. Negative lists / Workflow-owned detail — trimmed in main Skill, issue-dispatch, workflow-worktree, host-startup; suite-74-pinned Delegator first-beat list kept. `doc-maintenance.md` defers docking/archive/sink/cleanup to the Workflow finalize contract, keeps Host doc-impact judgment, drops the mandatory start/end doc check.
6. In-flight overlap — #204 presets/receipt-before-send, #205 reconciliation (moved into main Skill §Heartbeat), #206 classes and authorized-rows disclosure (final merged `worker-profiles.md` keeps authorized rows in the snapshot and forbids reinjecting whole tables — no conflict remains), #207 quota recovery (competing skeleton exhaustion line removed; `quota-packages.md` untouched), #210 cwd rule, #211 profile wording all preserved.

## Files Changed

- Templates: `templates/orchestrator/SKILL.md.tmpl`; `templates/orchestrator/references/{heartbeat-skeleton.txt,zcode-host-dispatch.md.tmpl,issue-dispatch.md,host-startup.md.tmpl,host-entry-matrix.md,doc-maintenance.md,qa-evidence.md,workflow-worktree.md}`; `templates/kaola-delegator/references/host-platforms.md.tmpl`.
- Generated: matching `skills/kaola-project-runner/` and `skills/kaola-delegator/references/host-platforms.md`; ten `main-skill-build.json` digests refreshed by the renderer.
- Tests retargeted to each moved rule's authoritative location: `tests/contract/test-issue-{41,68,72,92,118,133,187}-*.py`. Suites 65 and 162 untouched (owned by #209).
- `CHANGELOG.md`: Unreleased #208 entry, `Seats: restart not required`.

Rendered sizes (before → after; budget unchanged): main SKILL 17399→17373 (17408); heartbeat-skeleton 8191→3735; host-startup 8133→8095; zcode-host-dispatch 8181→8167; issue-dispatch 4861→4722; doc-maintenance 2460→1993; host-entry-matrix 5221→4888; qa-evidence 5849→5826; workflow-worktree 4858→4827; Delegator host-platforms 8170→8111; Delegator handoff 8186→8186 (references 8192).

## Test Coverage

- `./scripts/render-skills.py --check` — PASS, budgets OK (recorded final validation).
- 26 targeted contract suites (`tests/contract/test-issue-{92,72,68,118,49,94,41,133,75,74,70,168,119,65,52,86,187,162,97,148,123}-*.py`, `test-{zcode-heartbeat-contract,generated-skills,progressive-disclosure}.py`) at `f08da0b5`: all pass except the pre-existing #209 failures — suite 65 (2) and suite 162 (1) — identical to the pre-change baseline at `4206eafb`. Not masked or waived.
- Full `./scripts/validate.sh` not run (optional per dispatch). No live model probe, release, tag or install.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-delegator/references/host-platforms.md
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/doc-maintenance.md
- skills/kaola-project-runner/references/heartbeat-skeleton.md
- skills/kaola-project-runner/references/host-entry-matrix.md
- skills/kaola-project-runner/references/host-startup.md
- skills/kaola-project-runner/references/issue-dispatch.md
- skills/kaola-project-runner/references/qa-evidence.md
- skills/kaola-project-runner/references/workflow-worktree.md
- skills/kaola-project-runner/references/zcode-host-dispatch.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/kaola-delegator/references/host-platforms.md.tmpl
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/doc-maintenance.md
- templates/orchestrator/references/heartbeat-skeleton.txt
- templates/orchestrator/references/host-entry-matrix.md
- templates/orchestrator/references/host-startup.md.tmpl
- templates/orchestrator/references/issue-dispatch.md
- templates/orchestrator/references/qa-evidence.md
- templates/orchestrator/references/workflow-worktree.md
- templates/orchestrator/references/zcode-host-dispatch.md.tmpl
- tests/contract/test-issue-118-seat-cap.py
- tests/contract/test-issue-133-mission-ledger.py
- tests/contract/test-issue-187-delegator-any-host.py
- tests/contract/test-issue-41-orchestrator.py
- tests/contract/test-issue-68-heartbeat-snapshot.py
- tests/contract/test-issue-72-session-naming.py
- tests/contract/test-issue-92-permission-wake-recovery.py

## Documentation Docking

DOCKED. Checked files and no-impact reasons in `.cache/doc-docking.md`.

## Follow-Up Items

- #209 (existing, open): correct suites 65/162 expectations. Pinned-string changes from this run for its coordination: none in suites 65/162; retargeted in this run — test-118 (step-5 stop wording; dispatch pointer), test-133 (absent/terminal ledger rules), test-92 (`request_id` locator wording), test-68, test-72, test-41 (skeleton restatements), test-187 (codex probe narrative).
- No new follow-up filed.

## Readiness

READY — Host acceptance recorded; issue #208 closes on the verified merge.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-208/.cache/doc-docking.md
- kaola-workflow/archive/issue-208/.cache/final-validation.md
- kaola-workflow/archive/issue-208/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-208/finalization-summary.md
- kaola-workflow/archive/issue-208/mission-ledger.jsonl
- kaola-workflow/archive/issue-208/workflow-state.md
