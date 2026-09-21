# Finalization summary — issue-113

## Delivered
Issue #113 (ZCode output-token-max observability, v0.5.5 must-clear). Candidate `7c237c5` on
`workflow/issue-113` is f50dbde rebased onto main 6492000 (after #112's sink). Its code bytes are
identical to the Host-accepted candidate.

- `scripts/kaola-zcode-acp.py` translates the output-token-limit terminal to ACP
  `stopReason: "max_tokens"`. The terminal is `turn.failed` carrying `model_output_limit_exceeded`
  as `error.code` or `error.attribution.providerErrorCode`; the finish reasons `length`,
  `max_tokens`, `max_output_tokens` and `model_context_window_exceeded` are also recognised. An
  explicit cancel still wins.
- `scripts/kaola-acp-holder.py` records the reason verbatim in the receipt, in `record.json`
  `last_prompt.stop_reason`, and in a new `events.jsonl` `turn_ended` line.
- A contract-test regression gate with negative controls pins this.

Observability only. No model, effort or ceiling setting changed.

## Files Changed
- scripts/kaola-zcode-acp.py
- scripts/kaola-acp-holder.py
- 11 re-rendered generated copies under skills/*/scripts/
- tests/contract/fake-zcode-app-server.py
- tests/contract/test-zcode-acp-contract.py
- CHANGELOG.md

## Test Coverage
`test_output_token_max_terminal_reports_max_tokens` has 5 subtests. Before/after proof on the final
test bytes is in acceptance-a-final.txt: HEAD-7fc6fe3 adapter `FAILED (failures=5)`, candidate `OK`.

Controls:
- `test_ordinary_terminals_keep_refusal_and_end_turn`
- `test_cancel_still_wins_over_the_output_token_max_terminal`

End-to-end through the real holder: holder-persistence-check.txt.

## Validation
- Consumer repo, so no chain receipt: `run-chains` reported `chains_config_missing`.
- `.cache/final-validation.md` records `verdict: pass` with `validated_candidate_hash`
  36ec2f62…a735a9.
- Exact command, run on the rebased 7c237c5: `./scripts/render-skills.py --check` → PASS, budgets
  OK; then `env -u KAOLA_ZCODE_ENTRY -u KAOLA_ZCODE_NODE -u KAOLA_ACP_DISPATCHER
  -u KAOLA_ACP_HEARTBEAT_HOST -u KAOLA_ACP_HEARTBEAT_HOST_SOCKET ./scripts/validate.sh` →
  VALIDATE_EXIT=0, 0 FAILED (validate-rebased.log).

Acceptance legs:
- **(a) automated.** Red on the old adapter, green on the new one, as above.
- **(b) live UAT.** acceptance-b-live-v3.txt. Recipe v3 through the Runner with a scratch-HOME
  `provider_config.json` `providerModelRules` rule setting `maxOutputTokens.max: 256`. The receipt,
  `record.json` and `events.jsonl` all read `max_tokens`, and the scratch DB shows 4× `length` at
  256. Runs 1–2 (acceptance-b-live.txt) showed that the issue's prescribed `config.json`
  `limit.output` lever does not reach the model on the 3.12+ registration path.
- **(c) counting metric.** acceptance-c-draft.md: read-only sqlite commands, with zero exhausted
  turns on the real DB today.
- Host acceptance of all three ACs, and Fable final review PASS (issuecomment-5754838967).

Issue walk:
- Problem 1, adapter collapse → the adapter change plus test (a).
- Proposed change 2, holder persistence → holder-persistence-check plus the v3 receipts.
- Proposed change 3, re-render → render PASS.
- Acceptance (a), (b), (c) → as above.

Nothing is unexecuted.

## Changed Paths
From `finalize --check` (source-scoped; CHANGELOG.md is also in the commit but outside this list):
scripts/kaola-acp-holder.py, scripts/kaola-zcode-acp.py,
skills/{claude-code,codex,cursor-cli,devin,droid,dsh,grok,kimi-cli,opencode,zcode}-kaola-project-runner/scripts/kaola-acp-holder.py,
skills/zcode-kaola-project-runner/scripts/kaola-zcode-acp.py,
tests/contract/fake-zcode-app-server.py, tests/contract/test-zcode-acp-contract.py.
dirty_paths: none.

## Documentation Docking
DOCKED — see `.cache/doc-docking.md`. CHANGELOG entry added. Design/api docs already specify a
verbatim stop_reason that includes max_tokens, and no doc enumerates events.jsonl kinds.

## Follow-Up Items
- filed: #115 (bug, P3). validate.sh is not hermetic: Host-inherited KAOLA_* variables fail
  contract suites. Confirmed existing, with a non-empty body (2116 chars).
- Context, not filed by this run: #114 (preflight receipt field loss), tracked separately.
- Corrections to the #113 issue text, posted in the closing comment before close:
  - `config.json` `limit.output` does not reach the model on ZCode 3.12+; the working lever is the
    personal `providerModelRules` rule.
  - The exhaustion error writes no `model_usage` error row; count turns with ≥ 4 `length` rows.

## Readiness
READY — all 9 missions done, validation pass, docs docked, Host-accepted, final review PASS.
Closure decision: close #113.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-113/.cache/doc-docking.md
- kaola-workflow/archive/issue-113/.cache/final-validation.md
- kaola-workflow/archive/issue-113/.cache/mirror-digest.json
- kaola-workflow/archive/issue-113/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-113/acceptance-a-before.txt
- kaola-workflow/archive/issue-113/acceptance-a-final.txt
- kaola-workflow/archive/issue-113/acceptance-b-live-v3.txt
- kaola-workflow/archive/issue-113/acceptance-b-live.txt
- kaola-workflow/archive/issue-113/acceptance-c-draft.md
- kaola-workflow/archive/issue-113/acceptance-c-draft.v1.md
- kaola-workflow/archive/issue-113/finalization-summary.md
- kaola-workflow/archive/issue-113/holder-persistence-check.txt
- kaola-workflow/archive/issue-113/mission-list.md
- kaola-workflow/archive/issue-113/wire-contract.md
- kaola-workflow/archive/issue-113/workflow-state.md
