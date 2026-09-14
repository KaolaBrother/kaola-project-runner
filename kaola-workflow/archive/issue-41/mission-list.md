# Implement generated main orchestrator Skill kaola-project-runner (Issue #41)

Acceptance is https://github.com/KaolaBrother/kaola-project-runner/issues/41.
Background design (Issue #41 wins on conflict):
`/cursor/stores/bc-2883d4d5-8215-4f45-b452-c583deb344b5/docs/orchestrator-skill-design.md`.
Worktree: `/workspace/.kw/worktrees/issue-41` on `workflow/issue-41`.
`templates/grok-golden/` stays frozen. `skills/` is generated only. This Skill is a
control plane, not an eighth platform: no platform manifest or transport adapter.

1. item: Write failing acceptance tests for orchestrator generation, install flags, golden freeze, worker-transport preservation, and scenario meaning.
   status: done
   dispatched: [Issue 41 TDD tests](https://cursor.com/agents/bc-598a7560-7b8e-5e61-808a-82006d673ca9) — tests land on a branch from `workflow/issue-41`; RED proof in the worker report
   result: `workflow/issue-41` @ `fda090e`; suite in `tests/contract/test-issue-41-orchestrator.py` plus generated/installer/lifecycle/validate updates. RED proof `/cursor/stores/bc-2883d4d5-8215-4f45-b452-c583deb344b5/internal/issue-41-tdd-red.md`
2. item: Implement the orchestrator template, renderer inventory, installer `--no-orchestrator` and destination install, generated Skill, and docs that distinguish main orchestration from worker transport.
   status: done
   dispatched: [Issue 41 implement Skill](https://cursor.com/agents/bc-e31d6cf4-7359-5482-8aa7-d7908b732a01) — production on a branch from `workflow/issue-41` @ `fda090e`; do not weaken TDD
   result: frozen candidate `workflow/issue-41` @ `a19f528`; handback `/cursor/stores/bc-2883d4d5-8215-4f45-b452-c583deb344b5/internal/issue-41-implement.md`
3. item: Independent review of the frozen candidate against Issue #41 (correctness, test custody, no extra engine).
   status: done
   dispatched: [Issue 41 review candidate](https://cursor.com/agents/bc-56b913f6-0f13-55c6-bb72-f6290f2ee8f2) — frozen SHA `a19f528`; findings land at `/cursor/stores/bc-2883d4d5-8215-4f45-b452-c583deb344b5/internal/issue-41-review.md`
   result: orchestrator PASS — no admitted findings at `a19f528`; test custody `git diff --exit-code fda090e a19f528 -- tests/ scripts/validate.sh`. Review `/cursor/stores/bc-2883d4d5-8215-4f45-b452-c583deb344b5/internal/issue-41-review.md`

## PR #42 review continuation (2026-09-14)

- item: Repair PR review findings and establish merge readiness for Issue 41.
  status: done
  dispatched: Cursor CLI session cursor-cli-kaola-pr42-review in /Users/ylpromax5/Workspace/kaola-project-runner-pr42 on codex/pr-42-review; fixes and review evidence land in this worktree and archive/issue-41/.cache/pr-42-review.md. Main Codex owns acceptance and sink.
  result: Repairs delivered by Cursor at e4ef8c7 and accepted by main Codex; current closeout owned by kaola-workflow/pr-42-review.
