# Finalization Summary — issue-377

## Delivered

`collect` now finds a platform Runner beyond the caller's `--skills-root`, so a
seat is no longer stranded as `unknown / runner-missing` when the platform
Skill lives in the dispatch Skill root or the checkout's generated `skills/`
directory. Resolution order is `--skills-root`, the Skills root that holds the
running entry (its sibling Runner roots), then the checkout `skills/`; the
first existing `<platform>-kaola-project-runner/scripts/runtime-tmux.sh` wins,
and the row records the chosen `path`, `source` and `attempts` in
`evidence.runner`. `collect --item` uses the same resolution.

A `runner-missing` row is re-attempted by later collects with a bounded count:
`runner_missing_attempts` and `runner_missing_limit` (3) are recorded on the
row; at the bound the row stays `unknown / runner-missing` with
`runner_missing_exhausted` and the `runner-missing` recovery route from
`scripts/kaola-recovery-routes.py`. A later collect still resolves the Runner
if it becomes available, so the bound does not permanently poison the row. A
status receipt of `no-session` is now `unknown / session-gone`, not a lingering
`in-flight / no-result` row.

The new behavioral suite
`tests/contract/test-issue-377-runner-fallback.py` covers devin, dsh, droid and
opencode with codex as the control whose Runner is in the ordinary
`--skills-root`; it exercises the checkout `skills/` third layer, the installed
Skill-root second layer, recovery of a stored `runner-missing` row on the next
collect, the bound plus its route, recovery after the bound, and
`session-gone`. The suite is registered in `scripts/validate.sh`.

Generated surfaces were produced by `./scripts/render-skills.py --write` only;
no installed copy was edited. `CHANGELOG.md` has an `Unreleased` entry with
`Seats: restart not required`, and the orchestrator reference, `docs/api.md`
and `docs/dispatch-collect.md` describe the new behavior. The Grok Bot bridge
is at the content stage (`saveable: false`) for this content commit; the pin
commit remains a later release step.

## Candidate

Branch `workflow/issue-377` at
`ea3297e7b428b0ce947a510217d12741198c2213` (base main `7f01939e`).

- `ea3297e7` Fix #377: collect resolves fallback runners and retries
  runner-missing

Changed surface: `scripts/kaola-dispatch.py`,
`scripts/kaola-recovery-routes.py`, `scripts/validate.sh`, the new contract
suite, the orchestrator `dispatch-collect.md` source and generated Skill,
`docs/api.md`, `docs/dispatch-collect.md`, `CHANGELOG.md`, the content-stage
`templates/grok-bot/accepted-revision.json`, the regenerated `hosts/grok-bot`
products, and the regenerated worker Skill recovery-route copies and
`main-skill-build.json` manifests.

## Evidence

- Host acceptance of candidate `ea3297e7` on branch `workflow/issue-377`:
  fallback resolution, bounded retry semantics, `session-gone`, the
  four-platform contract suite, affected suites, render check, and no
  hand-edited installed copies.
- Pre-fix baseline with the same contract test on main `7f01939e`: 4 failures
  and 1 error (the four non-codex platforms stayed `runner-missing`; a gone
  session was `failed`). Post-fix: 5/5 OK.
- Affected suites at `ea3297e7`, exit 0 (10 suites):
  `test-issue-377-runner-fallback.py`, `test-issue-244-dispatch.py`,
  `test-issue-309-recovery-routes.py`, `test-issue-271-dispatch-help.py`,
  `test-generated-skills.py`, `test-issue-264-validate-lane-integrity.py`,
  `test-issue-255-lifecycle-state.py`, `test-issue-274-package-closure.py`,
  `test-issue-275-core-contracts.py`, `test-issue-306-bytecode-payload.py`.
  Log: `/tmp/kpr-377-validate-final.log`.
- Post-commit validation of the final test bytes:
  `./scripts/validate.sh --suite test-issue-377-runner-fallback.py`, exit 0,
  5/5 OK. Log: `/tmp/kpr-377-validate-postcommit.log`.
- `./scripts/render-skills.py --check`: PASS, budgets OK, content stage.
  `kaola-grok-bot-verify`: PASS.

## Known failures or unverified scope

- The fallback and retry are scoped to `collect` / `collect --item` as the issue
  requires. `execute`'s first admission still uses the explicit
  `--skills-root`; changing that selection semantic is a separate behavior.
- The contract suite uses fake Runner receipts and does not run live ACP smoke
  per platform; the issue is collect correlation, and the existing live-smoke
  integration boundary remains unexercised here.
- No installation was performed. A copy install needs the generated
  orchestrator Skill replaced before its new `kaola-dispatch.py` and recovery
  route are loaded; a symlink install sees them on the next call. No running
  seat restarts because these files are outside the operator restart set.
- The Grok Bot bridge is intentionally unpinned at the content stage; the
  release pin commit is not part of this run.

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
- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- scripts/kaola-dispatch.py
- scripts/kaola-recovery-routes.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/dispatch-collect.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/grok-bot/accepted-revision.json
- templates/orchestrator/references/dispatch-collect.md
- tests/contract/test-issue-377-runner-fallback.py

## Follow-Up Items

- None filed. The `execute` fallback boundary above is a scope decision, not a
  run-discovered defect; no separate issue was opened.

## Readiness

Candidate `ea3297e7` was accepted by the Host and validated at the affected
scope; ready for the merge sink (sink: merge, issue #377, branch
`workflow/issue-377`).

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-377/.cache/final-validation.md
- kaola-workflow/archive/issue-377/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-377/finalization-summary.md
- kaola-workflow/archive/issue-377/mission-ledger.jsonl
- kaola-workflow/archive/issue-377/workflow-state.md
