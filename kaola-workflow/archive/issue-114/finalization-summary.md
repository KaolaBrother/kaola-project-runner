# Finalization Summary — issue-114

## Delivered
The preflight receipt carries the adapter base fields again on the default acp transport. Every manifest defaults to `acp`, so `kaola-tmux.sh PLATFORM preflight` exec'd `kaola-acp.py` before `adapter_preflight` ran and `result`/`runtime`/`runtime_version`/`runtime_binary`/`detail` never reached the receipt (the issue's original base_json hypothesis was corrected in Mission 1). The acp preflight now also runs the adapter preflight and merges those fields under the ACP receipt, which wins on shared keys; `result` is `ready`, or `error` when the ACP receipt carries an error.

## Files Changed
scripts/kaola-tmux.sh, skills/*-kaola-project-runner/scripts/kaola-tmux.sh (10 generated copies), tests/contract/test-acp-contract.py, CHANGELOG.md. Candidate f39c602 rebased onto origin/main 34aaeae → e62a367 (only CHANGELOG Unreleased conflicted; all four entries #114/#117/#115/#116 kept adjacent).

## Test Coverage
test_runner_preflight_receipt_carries_adapter_base_fields (test-acp-contract.py) drives the real adapter path and asserts result/runtime_version/detail; fails on parent e7a2b57 (None != 'ready'), passes on the candidate.

## Validation
- At e62a367: `./scripts/render-skills.py --check` PASS (budgets OK).
- At e62a367: `./scripts/validate.sh` plain run exit 0 (7m56s); validate scrubbed the six inherited Host KAOLA_* names itself (#115), no manual strip; log validate-114.log.
- Record: .cache/final-validation.md, verdict pass, validated_candidate_hash 1c046d5e4238ded325a371798f3bf66f5c4f9754ba32c965799acf89a16c8ef6.
- Acceptance: Fable final review PASS on f39c602 (root cause confirmed on the real path; live preflight evidence on all ten platforms with real adapters; discriminating test; 47 suites OK in a scrubbed shell; renders byte-identical; scope clean). Host dispatched finalize as ACCEPTED.

## Changed Paths
- scripts/kaola-tmux.sh
- skills/{claude-code,codex,cursor-cli,devin,droid,dsh,grok,kimi-cli,opencode,zcode}-kaola-project-runner/scripts/kaola-tmux.sh
- tests/contract/test-acp-contract.py
- (docs, source-scope omitted by finalize) CHANGELOG.md

## Issue walk
- Base fields (result/runtime/runtime_version/runtime_binary/detail) present in the preflight receipt → kaola-tmux.sh acp block + focused contract test + ten-platform live evidence (Fable).
- OpenCode loopback detail (#112) visible again → carried via adapter `detail`; covered by the live table.
- No regression of the pty path or ACP receipt precedence → ACP wins on shared keys; full validate exit 0.

## Documentation Docking
DOCKED — see .cache/doc-docking.md.

## Follow-Up Items
None.

## Status
READY — close #114.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-114/.cache/doc-docking.md
- kaola-workflow/archive/issue-114/.cache/final-validation.md
- kaola-workflow/archive/issue-114/.cache/mirror-digest.json
- kaola-workflow/archive/issue-114/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-114/finalization-summary.md
- kaola-workflow/archive/issue-114/mission-list.md
- kaola-workflow/archive/issue-114/workflow-state.md
