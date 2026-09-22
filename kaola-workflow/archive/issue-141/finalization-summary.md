# Finalization Summary — issue-141

## Delivered
#141 was verified as a release gate for v0.5.8. No code change was needed. The #135 fix chain (847ca90 fix, 08eea7c test pin, b279678 docs) is on main. b279678 is NOT an ancestor of d2d29538 (v0.5.7), so the consumer failure reproduces only on the old accepted pin, which predates #135. On main, `platforms/cursor-cli.yaml:42` reads `acp_effort_config_id: "reasoning_effort;effort"`, and the generated skill copy matches.
Real-path proof from the main-tip checkout (4eccf34) used the repo's own `skills/cursor-cli-kaola-project-runner/scripts/runtime-tmux.sh start --tier default` with session `cursor-cli-KPR-i141-verify-probe` in the disposable Git repo /tmp/kpr-i141-probe. The start returned rc 0 and state ready. The effort apply resolved through `config_id: reasoning_effort` with `applied: true`, `advertised: true`, and candidates `[reasoning_effort, effort]`, value xhigh. The model landed as grok-4.7 and fast as false. The exact stop and the status check both report `residual_pids: []`. Receipts are in evidence/.
Evidence comment: https://github.com/KaolaBrother/kaola-project-runner/issues/141#issuecomment-5779924072. Host verdict: ACCEPTED.

## Files Changed
None (no implementation commit). Run records only.

## Test Coverage
None added; there was no behavior change. #135's 08eea7c already pins effective_selection.effort_config_id.

## Validation
`./scripts/render-skills.py --check` → PASS on the unchanged tree 4eccf34 (recorded in .cache/final-validation.md). `./scripts/validate.sh` was not run because there was no candidate. Acceptance leg: a live real-path Cursor ACP start/stop on the main tip (evidence/i141-start.json, i141-stop.json, i141-status.json).

## Changed Paths
[] (verification-only run)

## Documentation Docking
DOCKED — no impact (.cache/doc-docking.md).

## Follow-Up Items
None filed. The consumer migration is part of the v0.5.8 release step, after #140 also closes. That step tags v0.5.8 at a main tip that includes this verification context, puts a pin commit on workflow/grok-bot-pin-v0.5.8 (`templates/grok-bot/accepted-revision.json` stage pinned, commit R′, release v0.5.8), and runs `render-skills.py --check --require-pinned`. Consumers then check out v0.5.8, run `kaola-locate.py register --expect-revision R′`, confirm that `kaola-project-runner-locate --expect-revision R′` returns ok, and run `install-local.sh`.

## Status
READY — close #141, archive, no-op sink.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-141/.cache/doc-docking.md
- kaola-workflow/archive/issue-141/.cache/final-validation.md
- kaola-workflow/archive/issue-141/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-141/evidence/i141-comment.md
- kaola-workflow/archive/issue-141/evidence/i141-start.json
- kaola-workflow/archive/issue-141/evidence/i141-status.json
- kaola-workflow/archive/issue-141/evidence/i141-stop.json
- kaola-workflow/archive/issue-141/finalization-summary.md
- kaola-workflow/archive/issue-141/mission-ledger.jsonl
- kaola-workflow/archive/issue-141/workflow-state.md
