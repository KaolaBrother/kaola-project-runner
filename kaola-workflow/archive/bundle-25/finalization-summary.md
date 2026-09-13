# Finalization Summary

## Delivered

Issue #25: ACP holder `permit` / `cancel` / `stop` settle each pending permission `request_id` at most once under the same `Holder.lock` as prompt admission. Lookup → one JSON-RPC result on agent stdin → `pop`. A second settler is structured `error.code` `unknown-request` (not `already-answered`). `session/cancel` is unchanged. L0 `send --wait` keys are unchanged. Golden Grok bytes unchanged. Follow (#27) was not implemented.

## Files Changed

`scripts/kaola-acp-holder.py`, generated Skill holder copies and `references/acp.md`, `templates/references/acp.md.tmpl`, `tests/contract/test-acp-contract.py`, `tests/contract/hooks/sitecustomize.py`, README, CHANGELOG, `docs/api.md`, architecture / ACP Watch docs.

## Test Coverage

- `tests/contract/test-acp-contract.py` 18 OK at `e2b5b1c` (13 existing + #22 + 4 `Issue25PermitLockTests`).
- Baseline RED (HEAD `1928086`, unlocked holder): `Issue25PermitLockTests` 2 FAIL (two `permitted`; two cancelled JSON-RPC results). Proof: `.cache/tdd-red-proof.md`.
- Orchestrator re-ran `Issue25PermitLockTests` 4 OK after implement (`a76670c`) and after docs docking (`e2b5b1c`).
- `./scripts/render-skills.py --check` PASS (6 Skills).
- `./scripts/validate.sh` PASS at `e2b5b1c`.
- Independent review of frozen `a76670c`: correctness / test custody / trust boundary all PASS (0 findings). Docs docking commit `e2b5b1c` did not change holder bytes (`git hash-object scripts/kaola-acp-holder.py` still `dc62ae616ce0589b1baad62dee82603c65db5245`).
- Live tmux smoke per platform and live CLI UAT against a real ACP agent were not executed.

## Validation

`./scripts/validate.sh` — PASS, candidate hash `2d1bacd55394a7168dfb15979a342baa908963f03cba6dedbad7cca3dd72350e` at `e2b5b1c`.

`git diff --stat templates/grok-golden` — empty.

`run-chains.js`: `chains_config_missing` (consumer repo; finalize gates on agent-recorded `.cache/final-validation.md`).

## Changed Paths

finalize `--check` `changed_paths`:
`scripts/kaola-acp-holder.py`, `skills/claude-code-kaola-project-runner/references/acp.md`, `skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py`, `skills/cursor-cli-kaola-project-runner/references/acp.md`, `skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py`, `skills/devin-kaola-project-runner/references/acp.md`, `skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py`, `skills/grok-kaola-project-runner/references/acp.md`, `skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py`, `skills/kimi-cli-kaola-project-runner/references/acp.md`, `skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py`, `skills/opencode-kaola-project-runner/references/acp.md`, `skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py`, `templates/references/acp.md.tmpl`, `tests/contract/hooks/sitecustomize.py`, `tests/contract/test-acp-contract.py`.

`git diff --name-only origin/main...HEAD` also includes `CHANGELOG.md`, `README.md`, `docs/README.md`, `docs/acp-watch/README.md`, `docs/acp-watch/permit-lock.md`, `docs/api.md`, and `docs/architecture.md` (present on the branch, omitted from that check list).

## Documentation Docking

DOCKED in `.cache/doc-docking.md`.

## Follow-Up Items

None. Issue #27 (local follow stream) remains the open Watch successor; it was out of scope.

Review suspicion (not a defect, not filed): inbound `on_agent_request` / `$/cancel_request` / `on_agent_exit` still mutate `pending_permissions` without `Holder.lock`. Could not exhibit two JSON-RPC results for one id from that race.

## Readiness

READY for all-or-nothing closure and merge sink of issue #25.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/bundle-25/.cache/doc-docking.md
- kaola-workflow/archive/bundle-25/.cache/final-validation.md
- kaola-workflow/archive/bundle-25/.cache/implement-verify.md
- kaola-workflow/archive/bundle-25/.cache/mirror-digest.json
- kaola-workflow/archive/bundle-25/.cache/origin/selection-record.json
- kaola-workflow/archive/bundle-25/.cache/review-correctness.md
- kaola-workflow/archive/bundle-25/.cache/review-test-custody.md
- kaola-workflow/archive/bundle-25/.cache/review-trust-boundary.md
- kaola-workflow/archive/bundle-25/.cache/tdd-red-proof.md
- kaola-workflow/archive/bundle-25/finalization-summary.md
- kaola-workflow/archive/bundle-25/mission-list.md
- kaola-workflow/archive/bundle-25/workflow-state.md
