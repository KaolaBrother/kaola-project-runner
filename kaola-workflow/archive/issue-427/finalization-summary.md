# Finalization Summary — issue-427

## Delivered

Tool-collected terminal items are retirable. On `scripts/kaola-dispatch.py`:

1. **Settle-side collect identity** — a collected receipt that carries a
   `session` key must equal the item session (unchanged); one with no
   `session` key binds through a non-empty `acp_session_id` plus strict
   holder equality and repo equality (`same_repo`).
2. **Tool-side** — `collect` receipts now record the runner `session` they
   addressed (an explicitly different session is kept as evidence and yields
   `session-mismatch`); `execute` persists the plan-level `task_id` onto
   items that name none (an explicit item `task_id` still overrides —
   existing linkage semantics, documented).
3. **Dispositions** — `superseded` and `handed-off` per-item dispositions
   settle on the dead-holder and collect-terminal routes, reported as their
   own value; `repair` and every other value still refuse.
4. **Unlinked rows** — the exact-reclaim gate and `collect_terminal_settlement`
   accept `task_id: None` (the shape every prior `execute` wrote); a present
   foreign `task_id` still refuses.

Contract suite `tests/contract/test-issue-427-collect-binding.py` (21 tests)
registered in both validate.sh groups; rendered copies in-commit; docs
(`docs/api.md`, `docs/dispatch-collect.md`) and CHANGELOG Unreleased updated.

## Candidate

- Branch `workflow/issue-427`: `c2e72231` (binding + dispositions) →
  `f22f170f` (task-linkage repair). Base: main `e709bd39`.

## Evidence

- Suites on `f22f170f`: 427:21 / 426:53 / 421:45 / 412:31 / 372:13 / 397:27
  all exit 0; `render-skills --check` exit 0.
- Expert review (codex/astra) verdict **PASS**: 25 in-memory probes — copied
  receipts fail holder equality; foreign session/task_id refuse;
  superseded/handed-off do not bypass non-terminal or live checks; collect
  preserves task_id through merges; unchanged stale-collect/stopped-collect/
  refs-unindexed/linkage functions; generated copies match source.
- **Real-row proof (live `.kaola` state)**: the #426 run's own task row — three
  tool-written items with `task_id: None`, sessions stopped under their
  recorded holders — retired with typed receipts (rev 896):
  `i426-retire-routes` and `i426-bindfix` via `collect-terminal` with
  truthful `superseded` dispositions, `i426-fencefix` via exact-reclaim.

## Known failures / unverified scope

- Reviewer-accepted residual risks: legacy `acp_session_id` is checked for
  non-emptiness, not independently resolved (identity rests on genuine tool
  records, strict holder/repo equality, holder uniqueness); collision
  detection covers only supplied indices; Host dispositions/evidence remain
  trusted inputs.
- `profiles-20261026` remains unretired (no conforming archive citation —
  owner-level design call, unchanged from #426).

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- docs/dispatch-collect.md
- scripts/kaola-dispatch.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/hermes-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- tests/contract/test-issue-412-maintenance-owed-retire.py
- tests/contract/test-issue-426-retire-legacy-seats.py
- tests/contract/test-issue-427-collect-binding.py

## Follow-Up Items

- #425 (L1 prevent) implementation continues in parallel on its own branch;
  merge order #427 → #425 (rebase at finalize).
- #421 (L2 cleanup home) — with #427 merged, the adopted retire routes cover
  the known legacy shapes on this repo; consumer rows clear through their own
  Hosts per the settle.

## Final readiness

Ready: mission ledger 1 done / 0 in-flight after close; candidate frozen at
`f22f170f`; issue #427 acceptance basis met (fail-closed routes + 21-test
red-green suite + review PASS + live real-row proof); sink = merge to main,
close #427, archive/sink on -dev.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-427/.cache/final-validation.md
- kaola-workflow/archive/issue-427/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-427/finalization-summary.md
- kaola-workflow/archive/issue-427/mission-ledger.jsonl
- kaola-workflow/archive/issue-427/workflow-state.md
