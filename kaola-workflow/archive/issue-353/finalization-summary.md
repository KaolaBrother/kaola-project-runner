# Finalization Summary — issue-353

## Delivered

Issue #353 (bookkeeping 3): backstop sweep performance and correctness.

- 3a: the sweep forge lookup is one `gh api graphql` call per 50 issues (issue state plus merged `workflow/issue-N` PR heads). An answered but unusable call falls back to the serial per-issue path. A timeout answers `forge: "unavailable"` with no fallback. Merged heads are a set per issue. `KAOLA_SWEEP_FORGE_TIMEOUT` (default 20 s).
- 3b: a Host `--apply` reuses its one scan's forge facts. A node `--apply --batch` rebuilds items from the plan ids and re-verifies only them (no rescan). The batch event `sweep` carries `kept`, which the node apply writes to `sweep-kept`.
- 3c: `--apply` and `--record-empty` run `require_current` before any scan or action. A refusal exits 2 with the existing reason and a `recovery` command. Nothing is stopped, removed, pruned or written. A missing state file now refuses.
- 3d: one global `kaola-acp.py list --include-dead` per scan. An unanswered list skips S1/W1 items as `acp-unknown` (on main it read as "no live sessions" and could remove a worktree in use). Receipts carry `acp` and `timed_out`. The holder bounds the sweep tool child at `SWEEP_SCAN_TIMEOUT_SECONDS` 600 s with a process-group kill. A `timed_out` receipt is a failed scan (cooldown, `sideagent_sweep_scan_failed`, no record-empty).
- 3e: an overdue sweep (deferred more than one interval) runs at an idle boundary even with reconcile input pending. It never runs during a Host turn. No new timer. The Host close-out runs one `sweep --apply` (`templates/orchestrator/references/doc-maintenance.md`). `--dry-run` stays identity-free and read-only.
- CHANGELOG `## Unreleased`: Seats: restart required (`scripts/kaola-acp-holder.py` is in the operator restart set).

## Candidate

Branch `workflow/issue-353`, parent local `main` `b35165ff`.

- `e5af4034` — `Make the backstop sweep fast and safe at large worktree counts (#353)`

Acceptance candidate: `e5af4034`. Worktree clean. Pushed to `origin/workflow/issue-353`. This finalize adds no implementation commit.

Host acceptance: ACCEPTED.

## Evidence

- Full inventory `./scripts/validate.sh` (no `--suite`), run by the Host in the worktree at `e5af4034`, direct backend, clean environment: exit 0, 1338.75 s, no flake. Recorded in `.cache/final-validation.md` (verdict pass).
- Fail-on-main: 11 new tests in `tests/contract/test-issue-348-backstop-sweep.py` fail on `b35165ff`; the 15 existing tests pass there (`Ran 26 tests … FAILED (failures=11)`, `/tmp/kpr-i353-failonmain.log`).
- Focused suites on the candidate: 348 (27 OK), 255 (142 OK), 309 (8 OK), progressive-disclosure (15 OK) (`/tmp/kpr-i353-validate.log`). `./scripts/render-skills.py --check` PASS.
- Synthetic vrpai-scale `sweep --dry-run` (179 worktrees, 150 closed, fake gh with latency measured live: issue view ~1.15 s, pr list ~1.25 s, 50-issue graphql ~1.6 s): `b35165ff` 452.8 s / gh 358 / acp list 151; `e5af4034` 11.4 s / gh 4 / acp list 1; same 150 candidates; no worktree changed (`/tmp/kpr-i353-bench/results.jsonl`).
- Evidence comment: issuecomment-6259929327.

## Known failures and unverified scope

- No known product failure on `e5af4034`.
- Not reproduced and not claimed fixed: the vrpai heartbeat stall after 01:45, the vrpai node holder binding mismatch, and whether the observed vrpai sweep delay was the starvation mechanism (the mechanism itself is reproduced in a synthetic test).
- No real-project re-run; timings come from the synthetic fixture.
- Owner decision pending (HUMAN_DECISION_REQUIRED): the optional Delegator `sweep --dry-run` Skill text exceeds the Delegator Skill byte budget (4256 > 4096 B) and the candidate references are full. It is documented only in `docs/api.md`.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- scripts/kaola-acp-holder.py
- scripts/kaola-dispatch.py
- scripts/kaola-recovery-routes.py
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/antigravity-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/doc-maintenance.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/grok-bot/accepted-revision.json
- templates/orchestrator/references/doc-maintenance.md
- tests/contract/test-issue-255-lifecycle-state.py
- tests/contract/test-issue-348-backstop-sweep.py

## Follow-Up Items

- None filed. The Delegator Skill text is an owner decision recorded on issue #353, not a defect.
- No release, tag or install in this finalize.

## Readiness

Host accepted the change. The Host full-gate result on `e5af4034` is reused. Merge sink into local main, push to origin, close issue #353, release the claim label, archive.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-353/.cache/final-validation.md
- kaola-workflow/archive/issue-353/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-353/finalization-summary.md
- kaola-workflow/archive/issue-353/mission-ledger.jsonl
- kaola-workflow/archive/issue-353/workflow-state.md
