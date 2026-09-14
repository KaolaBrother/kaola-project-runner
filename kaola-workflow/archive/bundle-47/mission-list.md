# Add ongoing open-PR priority to the main Project Runner Skill (Issue #47)

Acceptance: https://github.com/KaolaBrother/kaola-project-runner/issues/47
Worktree: `/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-47`
Branch: `workflow/bundle-47`
Production writes only in this worktree: `templates/orchestrator/` and generated
`skills/kaola-project-runner/` via `./scripts/render-skills.py --write`. Do not
touch worker transport Skills or `templates/grok-golden/`. Stop before Workflow
finalize, merge, issue closure, or release.

1. item: Add focused #47 acceptance tests for ongoing PR priority meaning, contested-capacity vs parallel work, blocked-PR ownership without a global barrier, handoff/acceptance/stop-intake boundaries, heartbeat reflection, and worker-transport isolation — inspect next-action meaning, not a wording dump.
   status: done
   dispatched: self; tests land in `.kw/worktrees/bundle-47/tests/contract/test-issue-41-orchestrator.py` (Issue47 classes). RED proof in the worktree command output.
   result: PASS (tests authored). RED on current v0.2.1 Skill: Issue47OpenPrPriorityMeaning 4 FAIL (whenever-open-PRs, contested capacity, blocked-PR owner, handoff/acceptance/stop-intake). Worker isolation already green (policy absent from workers).

2. item: Put a concise open-PR priority rule in the orchestrator template and heartbeat skeleton, render `skills/kaola-project-runner/`, and update README/docs/CHANGELOG so they stay consistent.
   status: done
   dispatched: self; production in `.kw/worktrees/bundle-47` under `templates/orchestrator/` and generated `skills/kaola-project-runner/` via `./scripts/render-skills.py --write`; docs in README.md, `docs/architecture.md`, `docs/conventions.md`, CHANGELOG.md.
   result: PASS — Open PRs section in `templates/orchestrator/SKILL.md.tmpl`; heartbeat skeleton updated; rendered Skill package; docs/CHANGELOG aligned. Issue47 tests 4/4 plus worker isolation green.

3. item: Run `./scripts/render-skills.py --check`, `./scripts/validate.sh`, and a worktree-vs-main diff check; commit on `workflow/bundle-47`; write the run-folder report with files, proof, limits, and SHA. Stop before finalize.
   status: done
   dispatched: self; command receipts and commit SHA land in `kaola-workflow/bundle-47/` (report + this result).
   result: PASS — `--check` `render-skills: PASS (7 workers + kaola-project-runner)`; `validate.sh` exit 0 (27 orchestrator tests OK); worker/golden diff empty; commit `540a5ab178785a36051fb74406625c546da4c8b5`; report `kaola-workflow/bundle-47/delivery-report.md`. Stopped before finalize.

4. item: Revise `540a5ab` to the current Issue #47 owner rule: prefer selected authorized Workflow sync/merge when a PR is not required; conditional open-PR priority with safe parallel work on permitted CLIs; one compact heartbeat reminder; trim verbose Skill/tests/docs. Commit and update the delivery report. Stop before finalize.
   status: done
   dispatched: self; revised candidate lands on `workflow/bundle-47` in `.kw/worktrees/bundle-47`; report `kaola-workflow/bundle-47/delivery-report.md`.
   result: PASS — candidate `4a064b56caf8b0268d58feaafc377b718c6ca88c`; `--check` PASS; `validate.sh` exit 0 (25 orchestrator tests OK); report updated. Stopped before finalize.

5. item: Review-repair: trim Issue #47 tests to one compact check of Workflow merge preference, actionable-PR priority with permitted-CLI parallel work and blocked-PR ownership, heartbeat reflection, and worker isolation; make the Skill explicit that a PR is not opened merely for handoff when the authorized merge sink is suitable; Honor existing constraints. Commit and update the report. Stop before finalize.
   status: done
   dispatched: self; revised bytes on `workflow/bundle-47` in `.kw/worktrees/bundle-47`; report `kaola-workflow/bundle-47/delivery-report.md`.
   result: PASS — candidate `3a14e2ae8e1e6f9fd3cf471911c3deea394e9991`; `--check` PASS; `validate.sh` exit 0 (23 orchestrator tests OK, 22 pre-existing + 1 #47); tests +60/−1 vs v0.2.1; report updated. Stopped before finalize.

