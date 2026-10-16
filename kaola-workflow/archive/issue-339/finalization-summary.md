# Finalization Summary — Issue #339

## Delivered

- Refused `start` in `scripts/kaola-acp.py` when the ACP agent rejects the resolved model config option (`config_application.model.applied` is `false` with `error`), returning `result: "refused"`, `reason: "model-config-option-rejected"`, top-level `error` carrying the agent's `config-option-failed` (`-32602`) rejection, a self-documenting `detail` naming the option id and value, and reclaiming the just-started holder (`stop_started_holder` -> `holder_reclaimed: true`, `mutation_status: "not_started"`) at exit code 1.
- Added `--allow-unapplied-model` on `start` so a caller may explicitly opt in to the agent's own model selection (`state: "ready"`, `applied: false`, and `error` retained in the receipt and `status` `start_evidence`).
- Kept unadvertised options (`no-advertised-config-option`), `applied_via: "argv"`, rejected effort/Fast options, and `effective_selection` readback mismatches unchanged as limitation/evidence receipts.
- Added `tests/contract/test-issue-339-model-option-rejected.py` and registered it in `scripts/validate.sh` (`python_suites_all` and `python_suites_b`), updated legacy tests in `test-acp-contract.py`, `test-issue-130-pty-retired.py`, and `test-issue-254-opencode-model.py`, documented the behavior in `docs/api.md`, and regenerated all 11 worker Skills.

## Candidate

- Branch: `workflow/issue-339`
- Commits:
  - `1114a89da36308f6ab0c8d6b0cc982d43e635ee0` — `chore(release): open post-v0.9.14 content cycle — grok-bot bridge back to unpinned content stage`
  - `fff146c1f47fb1d4a9f723dbfeefcd6db013e421` — `fix(acp): refuse start when resolved model config option is rejected (#339)`
  - `8692fd90` — `Merge remote-tracking branch 'origin/main' into workflow/issue-339`

## Evidence

- Validation record: `kaola-workflow/issue-339/.cache/final-validation.md` (`verdict: pass`, `validated_candidate_hash: e81f85e0788e96de85b731897e0217a0758f61237a2982cc453c91ee2b99cf23`)
- Pre-merge 7-suite run on `fff146c1`: `test-issue-339-model-option-rejected.py`, `test-issue-130-pty-retired.py`, `test-acp-contract.py`, `test-issue-254-opencode-model.py`, `test-issue-331-effort-model-id.py`, `test-issue-244-dispatch.py`, `test-issue-264-validate-lane-integrity.py` + `render-skills.py --check` all PASS (exit 0).
- Post-merge 4-suite run on `8692fd90`: `test-issue-339-model-option-rejected.py`, `test-issue-254-opencode-model.py`, `test-issue-331-effort-model-id.py`, `test-issue-264-validate-lane-integrity.py` + `render-skills.py --check` all PASS (exit 0).
- Verbatim receipt 1 (default `start` rejected, `rc=1`):
  ```json
  {"result":"refused","reason":"model-config-option-rejected","action":"start","error":{"code":"config-option-failed","config_id":"model","detail":{"code":-32602,"message":"unknown model option [\"opencode-go\",\"deepseek-v4.1-flash\"]"}},"detail":"the dsh agent rejected the resolved model option model='[\"opencode-go\",\"deepseek-v4.1-flash\"]' (unknown model option [\"opencode-go\",\"deepseek-v4.1-flash\"]); the session was stopped before this start returned, and no other model was substituted; pass --allow-unapplied-model to accept the agent's own selection instead.","config_application":{"model":{"applied":false,"config_id":"model","error":{"code":"config-option-failed","config_id":"model","detail":{"code":-32602,"message":"unknown model option [\"opencode-go\",\"deepseek-v4.1-flash\"]"}},"mapped":true,"requested_id":"opencode-go/deepseek-v4.1-flash","value":"[\"opencode-go\",\"deepseek-v4.1-flash\"]"}},"effective_selection":{"effective_effort":"","effective_model":"[\"deepseek-official\",\"deepseek-v4-flash\"]","effort_config_id":"reasoning_effort"},"host_session_stopped":true,"holder_alive":false,"holder_reclaimed":true,"mutation_performed":false,"mutation_status":"not_started"}
  ```
- Verbatim receipt 2 (`start --allow-unapplied-model`, `rc=0`):
  ```json
  {"state":"ready","config_application":{"model":{"applied":false,"config_id":"model","error":{"code":"config-option-failed","config_id":"model","detail":{"code":-32602,"message":"unknown model option [\"opencode-go\",\"deepseek-v4.1-flash\"]"}},"mapped":true,"requested_id":"opencode-go/deepseek-v4.1-flash","value":"[\"opencode-go\",\"deepseek-v4.1-flash\"]"}},"effective_selection":{"effective_effort":"","effective_model":"[\"deepseek-official\",\"deepseek-v4-flash\"]","effort_config_id":"reasoning_effort"},"start_evidence_recorded":true}
  ```

## Known failures and unverified scope

- None in changed scope. As accepted by the Host, `stop_started_holder` updates the refused receipt in place, leaving the pre-stop `state: "ready"` key alongside `result: "refused"`, `host_session_stopped: true`, `holder_alive: false`, `holder_reclaimed: true`, and `mutation_status: "not_started"`, matching the existing `explicit-selection-unverified` and `host-model-unverified` precedents.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- docs/api.md
- scripts/kaola-acp.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- tests/contract/test-acp-contract.py
- tests/contract/test-issue-130-pty-retired.py
- tests/contract/test-issue-254-opencode-model.py
- tests/contract/test-issue-339-model-option-rejected.py

## Follow-Up Items

- None.

## Readiness

- Ready to finalize, archive, and merge-sink (#339 accepted by Host `zcode-KPR-orchestrator-main`).

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-339/.cache/final-validation.md
- kaola-workflow/archive/issue-339/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-339/finalization-summary.md
- kaola-workflow/archive/issue-339/mission-ledger.jsonl
- kaola-workflow/archive/issue-339/workflow-state.md
