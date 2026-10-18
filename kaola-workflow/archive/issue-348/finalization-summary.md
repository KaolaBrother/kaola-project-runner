# Finalization Summary — issue-348

## Delivered

Issue #348: the Sideagent backstop sweep cleans up residues that the main close-out flow missed. It is deterministic, conservative and idempotent.

- `kaola-dispatch.py sweep --repo ROOT (--dry-run | --apply | --record-empty)` writes a `kaola-sweep/1` receipt. `--dry-run` writes nothing. `--apply` runs only under the verified Host carrier or a bound node with a matching `sideagent_node_batch` `sweep` plan, and it re-verifies each planned item at deletion time. `--record-empty` is Host-only.
- Closed rule set. Nothing else is touched:
  - S1: verified worker sessions of CLOSED issues, exact-stopped with `--expected-holder-instance-id`.
  - W1: clean, unlocked, merged linked worktrees of CLOSED issues inside the project, removed without `--force`.
  - W2: prunable worktree metadata.
  - F1: stale `.kaola/*.tmp` files older than 24 h. Symlinks are excluded.
- Unsafe or uncertain items are kept and reported in `alerts["sweep-kept"]` as `{why, evidence, next}`. Issue-linked items are skipped as `forge-unknown` when the forge is unavailable.
- The receipt is `maintenance.last_sweep`, one overwritten current fact, plus the Runner events `sideagent_sweep_settled`, `sideagent_sweep_empty` and `sideagent_sweep_scan_failed`. No new ledger.
- Due mechanism: a node-mode Host carrier evaluates the sweep at its existing relay boundaries (idle tick and Host turn end). It is due on the first run, after an upgrade (Accepted revision change), after a HEAD move, or when the `KAOLA_SWEEP_INTERVAL_HOURS` interval has passed (default 24 h). There is no new timer.
  - Not due: no scan, node or wake.
  - Due with no candidates: `--record-empty`. No node, wake or Host turn.
  - Due with candidates: exactly one keyed node batch. It never starts during a Host turn and never delays reconciliation.
- Holder feature `sideagent-sweep/1`. `docs/api.md`, README, `doc-maintenance.md` and CHANGELOG Unreleased are updated. Seats: restart required.
- Full-gate follow-up: four sweep codes now have recovery routes (`no-longer-candidate`, `permission-pending`, `repo-missing`, `turn-active`; #309). The `docs/api.md` prose names `reported_drift` without listing its values (#168).

## Candidate

Branch `workflow/issue-348`, parent local `main` `69fd4ddd73e92f95d1030c0fa4cff5cf53fe2948` (after #349).

- `002220ea10cf193a74be69706bd76e39fd681f0c`: `Add the Sideagent backstop sweep for missed close-out cleanup (#348)`. This is 539d0099 rebased onto 69fd4ddd.
- `9566f043184f1ae81093a62dd73c8127afa11f84`: `Route the sweep refusal codes and name reported_drift without values (#348)`

Acceptance candidate: `9566f043184f1ae81093a62dd73c8127afa11f84`. Worktree clean. Not pushed. This finalize does not add an implementation commit.

Host acceptance: ACCEPTED.

## Evidence

- Full inventory `./scripts/validate.sh` (no `--suite`), worktree clean at `9566f043`: 129 suites, exit 0, 1507.2 s. Log: `/tmp/kpr-run/full-validate-348-9566f043.log`. The same commit is still the worktree HEAD, so that voucher is reused and no suite is re-run.
- The first full gate on `002220ea` found two deterministic integration gaps: `test-issue-168-drift-enumeration.py` and `test-issue-309-recovery-routes.py`. Log: `/tmp/kpr-run/full-validate-348-002220ea.log`. `9566f043` fixed both, and the focused suites 168/309/348/264-lane-integrity passed (`/tmp/kpr348-gatefix-suites.log`) before the green full gate.
- Fail-on-main for `tests/contract/test-issue-348-backstop-sweep.py` at `d4cdad99`: exit 1, with 7 failures and 8 errors (`/tmp/kpr348-main2-run.log`). After the fix: 15 tests, exit 0.
- Mission ledger `kaola-workflow/.ledger/issue-348.jsonl`: five missions `done`. Those lines are not rewritten.

## Known failures and unverified scope

- No known product failure on `9566f043`.
- No live Host run of the sweep is claimed. Behavior is proven with temporary repositories, a fake forge and fake Runner sessions only.
- The sweep deliberately does not scan full project documents. `doc-maintenance.md` keeps "no timer-driven full documentation scan" true.
- Host boundary for this finalize: merge into local main only. Do not push. Do not close issue #348. Do not add a GitHub comment. Do not release, tag, install, or open a new issue. Keep-open is that deferral. Offline mode makes no forge call, so the claim label is not released here.
- Post-merge `./scripts/render-skills.py --write` and `--check` run on local main after the sink. No validate suite is re-run. The full gate already passed on this same commit.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- README.md
- docs/api.md
- scripts/kaola-acp-holder.py
- scripts/kaola-dispatch.py
- scripts/kaola-record-contract.py
- scripts/kaola-recovery-routes.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/antigravity-kaola-project-runner/scripts/kaola-record-contract.py
- skills/antigravity-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-record-contract.py
- skills/claude-code-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-record-contract.py
- skills/codex-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-record-contract.py
- skills/devin-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-record-contract.py
- skills/droid-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-record-contract.py
- skills/dsh-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-record-contract.py
- skills/grok-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/doc-maintenance.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kaola-project-runner/scripts/kaola-record-contract.py
- skills/kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/opencode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/zcode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/references/doc-maintenance.md
- tests/contract/test-issue-348-backstop-sweep.py

## Follow-Up Items

- None filed. No run-discovered defect requires a new issue. `searched:` not applicable, because nothing was filed.

## Readiness

Host accepted the change. The full-gate voucher on `9566f043` is reused. The local merge-sink and archive proceed. Issue #348 stays open. Publication to the remote waits for the Host.

## Finalize Findings

### claim_release_skipped_offline

This finalize released no claim: KAOLA_WORKFLOW_OFFLINE=1, so the release returned before making any forge call. Nothing local records whether this run was ever claimed online, so this does not assert the artifacts are there — but IF the claim was posted, the `workflow:in-progress` label and the `kw:claim` marker comment are still on the issues below. The marker expires after 24h; the label does not, and either one blocks a later claim of that issue until it is removed.

Issues whose claim release was skipped:

- #348

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-348/.cache/final-validation.md
- kaola-workflow/archive/issue-348/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-348/finalization-summary.md
- kaola-workflow/archive/issue-348/mission-ledger.jsonl
- kaola-workflow/archive/issue-348/workflow-state.md
