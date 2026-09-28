verdict: DOCKED

Checked files:
- `templates/orchestrator/SKILL.md.tmpl` → `skills/kaola-project-runner/SKILL.md`: seat lifecycle stated once in step 5; #205 one-time reconciliation after a Skill update in §Heartbeat; negative lists trimmed.
- `templates/orchestrator/references/{heartbeat-skeleton.txt,zcode-host-dispatch.md.tmpl,issue-dispatch.md,host-startup.md.tmpl,host-entry-matrix.md,doc-maintenance.md,qa-evidence.md,workflow-worktree.md}` and `templates/kaola-delegator/references/host-platforms.md.tmpl` → matching generated references (render --check PASS, budgets unchanged).
- `CHANGELOG.md`: Unreleased entry for Issue #208 with `Seats: restart not required`.
- `docs/host-entry-evidence.md`: already holds the codex-acp 1.13.1 `SKILL-NOT-LOADED` history and the kimi/#119/#126 measurement lineage removed from routine references — no edit needed.
- `docs/zcode-host.md`: still accurate (the drop/keep subtraction rule remains in `references/heartbeat-skeleton.md`; permission-wake locator semantics unchanged).
- `docs/issue-dispatch-display.md`: consumer display semantics unchanged; absent ledger still falls back to unknown.
- `README.md`, `docs/architecture.md`, `docs/conventions.md`: describe ownership at a level this change does not alter — no impact.

No API, CLI, transport, setup, environment or example change: prompt/reference consolidation only. `templates/grok-golden/`, `platforms/`, operator-test paths untouched.
