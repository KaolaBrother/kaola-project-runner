# Finalization Summary — issue-350

## Delivered

Issue #350: automatic Worker selection skips presets marked `computer-use-only`.

- Platform manifests may set `<tier>_model_roles` (and `default_model_roles`) to the closed value `computer-use-only`. Absent or empty means none. An unknown, empty, or repeated token rejects that catalog row. Profile prose is not a role. Only `codex/luna` sets the mark.
- `project --authorization` candidates carry `roles`. The Sideagent node chain (`_node_chain` / `_node_fallback`, including a dsh `turn_failed`) drops every Worker whose roles include `computer-use-only`. The filter does not name the preset.
- Explicit Host dispatch of a granted marked preset stays available. Grants, exclusions, holds, and availability are unchanged. A chain that becomes empty fails once on the existing exhausted path. There is no new wake reason.
- Seats: restart required. `scripts/kaola-acp-holder.py` and `platforms/codex.yaml` are in the operator restart set. This content commit leaves the Grok Bot bridge unpinned (`saveable: false`).

## Candidate

Branch `workflow/issue-350`, parent local `main` `aa362c928223de0de4c86495f2e8fab0b198a261`.

- `8b800f2776a7a83baff5dcf9abf11064230d3397` — `fix: skip computer-use-only presets in automatic Worker selection (#350)`

Acceptance candidate: `8b800f2776a7a83baff5dcf9abf11064230d3397`. Worktree clean. Not pushed. This finalize does not add an implementation commit.

Host acceptance: ACCEPTED.

## Evidence

- Full inventory `./scripts/validate.sh` (no `--suite`), worktree clean at `8b800f27`: 130 suites, exit 0, wall 1509.62 s. Log: `/tmp/kpr-run/full-validate-350-8b800f27.log` (`validate: candidate: 8b800f27 (clean)`, `VALIDATE_EXIT=0`). No flake. The same commit is still the worktree HEAD, so that voucher is reused and the suite is not re-run.
- Host voucher: fail-on-main at `aa362c92` was 7 tests, 5 failures and 2 errors. Focused suites 350, 324, 336, 346, 264 plus render were green. Host re-ran the repro on the worktree; the repaired chain is `claude-code/haiku`, `devin/default`, `opencode/default`, `zcode/default`, and `codex/luna` is excluded.
- Mission ledger `kaola-workflow/.ledger/issue-350.jsonl`: two missions `done`. Those lines are not rewritten.

## Known failures and unverified scope

- No known product failure on `8b800f27`.
- Host boundary for this finalize: merge into local main only. Do not push. Do not close issue #350. Do not add a GitHub comment. Do not release, tag, install, or open a new issue. Keep-open is that deferral. Offline mode makes no forge call, so the claim label is not released here.
- Post-merge `./scripts/render-skills.py --write` and `--check` run on local main after the sink. No validate suite is re-run; the full gate already passed on this same commit.

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
- platforms/codex.yaml
- scripts/kaola-acp-holder.py
- scripts/kaola-dispatch.py
- scripts/render-skills.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/platform.yaml
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/profile-catalog.md
- skills/kaola-project-runner/references/sideagent-node.md
- skills/kaola-project-runner/references/worker-profiles.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/grok-bot/accepted-revision.json
- templates/orchestrator/references/profile-catalog.md.tmpl
- templates/orchestrator/references/sideagent-node.md
- templates/orchestrator/references/worker-profiles.md.tmpl
- tests/contract/test-issue-350-computer-use-roles.py

## Follow-Up Items

- None filed. No run-discovered defect requires a new issue. `searched:` not applicable; nothing was filed.

## Readiness

Host accepted the change. The full-gate voucher on `8b800f27` is reused. Local merge-sink and archive proceed. Issue #350 stays open. Publication to the remote waits for the Host.

## Finalize Findings

### claim_release_skipped_offline

This finalize released no claim: KAOLA_WORKFLOW_OFFLINE=1, so the release returned before making any forge call. Nothing local records whether this run was ever claimed online, so this does not assert the artifacts are there — but IF the claim was posted, the `workflow:in-progress` label and the `kw:claim` marker comment are still on the issues below. The marker expires after 24h; the label does not, and either one blocks a later claim of that issue until it is removed.

Issues whose claim release was skipped:

- #350

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-350/.cache/final-validation.md
- kaola-workflow/archive/issue-350/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-350/finalization-summary.md
- kaola-workflow/archive/issue-350/mission-ledger.jsonl
- kaola-workflow/archive/issue-350/workflow-state.md
