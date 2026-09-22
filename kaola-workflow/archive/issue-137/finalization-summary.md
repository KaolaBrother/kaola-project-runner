# Finalization summary — issue-137

## Delivered
Owner-accepted split (2026-09-22 evening) of the rewritten #137 design into two short procedure
layers; no runtime sampling, upstream tracking, new gate, classifier, or subsystem.
- Layer 1 (Host prevention): Project Runner `workflow-worktree.md` gains "Host shell cwd": never
  `cd` into `.kw/worktrees/` or `kaola-workflow/issue-N/`; absolute paths, `git -C`, or a subshell;
  return to the project root before finalize or sink; subagents follow the same rule; a bricked
  Host reports `brick`, asks to be replaced, and stops acting.
- Layer 2 (Delegator recovery): new Kaola-Delegator reference `host-brick.md` (901 B) — outer
  Agent exact-stops the Host (`--expected-holder-instance-id`), starts a new standard-named Host at
  the project root under current authorization, continues from `.kaola/heartbeat-prompt.json`,
  mission ledgers, and Runner receipts; no `--resume` of the bricked `sess_*` until proven live.
  `handoff.md` had 29 B headroom and progressive disclosure requires a SKILL.md link, so the
  Delegator SKILL.md links it (4095/4096 B after wording-only trims; pinned phrases kept).

## Files Changed
templates/orchestrator/references/workflow-worktree.md; templates/kaola-delegator/SKILL.md.tmpl;
templates/kaola-delegator/references/host-brick.md (new); CHANGELOG.md; generated
skills/kaola-project-runner/references/workflow-worktree.md, skills/kaola-delegator/SKILL.md,
skills/kaola-delegator/references/host-brick.md, and 10 worker scripts/main-skill-build.json.

## Test Coverage
Text-only change. Existing gates cover it: render budgets (reference_bytes, external_skill_bytes),
test-progressive-disclosure.py (new reference linked by relative path, never inlined),
test-generated-skills.py (#132 `sweep=` line pin), test-issue-74 (186 assertions, 0 failed),
kaola-grok-bot-verify. No new test: the Owner scoped this to short procedure text.

## Validation
- `./scripts/render-skills.py --check` — PASS (budgets OK)
- `./scripts/validate.sh` — rc=0 at 02e107b and again at 4795cce (log validate-137.log, 654 lines, 0 FAIL/ERROR)
- `git diff --check 673401a 4795cce` — clean
- Host acceptance: ACCEPTED at 02e107b (2026-09-22); 4795cce adds only the CHANGELOG entry and was re-validated
- Record: .cache/final-validation.md, validated_candidate_hash 8e954074204791c6…

## Changed Paths
- CHANGELOG.md
- skills/*/scripts/main-skill-build.json (10 workers, regenerated)
- skills/kaola-delegator/SKILL.md
- skills/kaola-delegator/references/host-brick.md
- skills/kaola-project-runner/references/workflow-worktree.md
- templates/kaola-delegator/SKILL.md.tmpl
- templates/kaola-delegator/references/host-brick.md
- templates/orchestrator/references/workflow-worktree.md

## Issue walk
- Fault model / Layer 1 prevention → workflow-worktree.md "Host shell cwd".
- Layer 2 recovery → host-brick.md + SKILL.md link.
- Layer 3 (upstream ZCode fix/tracking) and runtime sampling of the nine other Hosts → excluded by
  the Owner's delivery split (issue comment 5776458051); not deferred work of this run.

## Documentation Docking
DOCKED — see .cache/doc-docking.md.

## Follow-Up Items
- No new defects discovered; no follow-up issue filed.
- Delegator SKILL.md now at 4095/4096 B — headroom note, not a defect.

## Readiness
READY — closure decision: close #137.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-137/.cache/doc-docking.md
- kaola-workflow/archive/issue-137/.cache/final-validation.md
- kaola-workflow/archive/issue-137/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-137/finalization-summary.md
- kaola-workflow/archive/issue-137/mission-ledger.jsonl
- kaola-workflow/archive/issue-137/workflow-state.md
