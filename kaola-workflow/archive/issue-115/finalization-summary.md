# Finalization Summary — issue-115

## Delivered
`./scripts/validate.sh` is hermetic against a dispatching Host's environment: before any suite runs it unsets every inherited `KAOLA_*` name except its own `KAOLA_VALIDATE_*` knobs and prints `validate: scrubbed inherited env: <names|none>`.

## Files Changed
- scripts/validate.sh (+15)
- CHANGELOG.md (+13, new `## Unreleased` section)

## Test Coverage
No new test file: the gate itself is the regression surface. The two previously failing cases (`test-issue-73-canonical-root.py::TestRunnerDispatchIsAcpOnly::test_acp_start_under_a_dispatcher_passes_the_shell_to_the_acp_resolver`, `test-zcode-acp-contract.py` resolve-runtime fail-closed) pass under an inherited six-name Host environment.

## Validation
- Implementer run: `./scripts/validate.sh` in worktree at abdd116 bytes, shell carrying KAOLA_ACP_DISPATCHER KAOLA_ACP_HEARTBEAT_HOST KAOLA_ACP_HEARTBEAT_HOST_SOCKET KAOLA_CLAUDE_PROFILE_REQUIRED KAOLA_ZCODE_ENTRY KAOLA_ZCODE_NODE, no manual stripping → VALIDATE_EXIT=0; scrub line named all six; sweep residual_pids []. Log: validate-abdd116.log.
- `./scripts/render-skills.py --check` → PASS, no generated changes.
- Host acceptance: injected six-name reproduction, validate exit 0, zero residuals (/tmp/kpr-i115-host-validate.log).
- Fable final review: PASS (https://github.com/KaolaBrother/kaola-project-runner/issues/115#issuecomment-5755708501).
- Record: .cache/final-validation.md, verdict pass, validated_candidate_hash 851bdbbb4da9ac9c63935fdcfdb183efb7747e09a2f5262409e1dd74dd73389f.

## Changed Paths
- CHANGELOG.md
- scripts/validate.sh

## Issue walk
- "scrub Host-binding KAOLA_* names before any suite runs" → validate.sh scrub block, placed before the first `watched` suite.
- "print which names it removed" → scrub line (log line 1).
- "hermetic wherever it is launched from" → inherited-env run exit 0 (implementer + Host).

## Documentation Docking
DOCKED — see .cache/doc-docking.md.

## Follow-Up Items
None filed. Review note (non-blocking): opt-in caller knobs KAOLA_ISSUE74_EVIDENCE, KAOLA_RUNNER_DEBUG, KAOLA_MODEL_PROBE_TIMEOUT are dropped under validate; rename to KAOLA_VALIDATE_* if ever needed there.

## Status
READY — close #115.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-115/.cache/doc-docking.md
- kaola-workflow/archive/issue-115/.cache/final-validation.md
- kaola-workflow/archive/issue-115/.cache/mirror-digest.json
- kaola-workflow/archive/issue-115/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-115/finalization-summary.md
- kaola-workflow/archive/issue-115/mission-list.md
- kaola-workflow/archive/issue-115/workflow-state.md
