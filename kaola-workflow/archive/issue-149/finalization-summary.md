# Issue #149 finalization summary

## Delivered

Measured one authenticated Codex ACP Host session under a temporary shadow `HOME` and `CODEX_HOME`. Codex CLI 0.156.1 through `codex-acp` 1.13.0 accepted `/compact`; the ACP transcript and Codex rollout prove compaction completed. The installed user-level `SessionStart(compact)` hook logging wrapper had no invocation, including after a follow-up turn loaded on the same native session. A direct positive control wrote the expected log record. The shadow directory containing the copied `auth.json` was removed. The issue's conditional ALIGN step was deferred, so no recovery template or generated Skill was changed. The Host accepted this delivery as PASS.

## Files Changed

Only `kaola-workflow/issue-149/**`: measurement receipts, verifier, Workflow state, validation and documentation records, and this summary.

## Test Coverage

- `python3 kaola-workflow/issue-149/evidence/measurement/verify-receipts.py` — PASS on the frozen candidate. It checks authentication, exact versions/config, ACP and Codex compaction receipts, absent hook log, positive control, cleanup, known baseline pin error, and #149-only diff scope.
- Manual ACP integration: `evidence/measurement/acp_probe.py` and `acp_followup.py` — one native session, completed compaction and follow-up. Transcript and rollout receipts are in `evidence/measurement/`.
- Host acceptance: PASS on the measurement and alignment deferral. The Host independently reproduced the existing pin preflight failure on clean main.

## Validation

`kaola-workflow-run-chains.js --project issue-149` reported `chains_config_missing`: this Bash/Python consumer has no `test:kaola-workflow:*` npm scripts. The non-npm final validation record in `.cache/final-validation.md` binds the PASS verifier command to the candidate hash. `./scripts/render-skills.py --check` and `./scripts/validate.sh` each exited 1 at the pre-existing Grok Bot accepted-pin preflight: current main already contains `kaola-workflow/release/validate-v0559.log` beyond accepted pin `628c8d50a55b`. This run did not modify the pin, tests, templates, or generated outputs. Exact logs and exit receipts are under `evidence/measurement/`.

## Changed Paths

None outside `kaola-workflow/issue-149/**`.

## Documentation Docking

`DOCKED` in `.cache/doc-docking.md`. No product documentation change applies; the measurement itself is documented in the evidence directory.

## Follow-Up Items

The Grok Bot pin/release state is a known external baseline owned elsewhere. No #149 fix or new follow-up issue was filed for it. No PR was opened.

## Readiness

Ready for issue #149 correction comment, Workflow close/archive, and sink-merge after the read-only finalize checklist confirms its preconditions.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-149/.cache/doc-docking.md
- kaola-workflow/archive/issue-149/.cache/final-validation.md
- kaola-workflow/archive/issue-149/evidence/measurement/README.md
- kaola-workflow/archive/issue-149/evidence/measurement/acp-compact-events.json
- kaola-workflow/archive/issue-149/evidence/measurement/acp-followup-summary.json
- kaola-workflow/archive/issue-149/evidence/measurement/acp-followup-transcript.jsonl
- kaola-workflow/archive/issue-149/evidence/measurement/acp-summary.json
- kaola-workflow/archive/issue-149/evidence/measurement/acp-transcript.jsonl
- kaola-workflow/archive/issue-149/evidence/measurement/acp_followup.py
- kaola-workflow/archive/issue-149/evidence/measurement/acp_probe.py
- kaola-workflow/archive/issue-149/evidence/measurement/auth-status.exit
- kaola-workflow/archive/issue-149/evidence/measurement/auth-status.txt
- kaola-workflow/archive/issue-149/evidence/measurement/codex-rollout-compact-events.json
- kaola-workflow/archive/issue-149/evidence/measurement/hook-firings-control.jsonl
- kaola-workflow/archive/issue-149/evidence/measurement/install.exit
- kaola-workflow/archive/issue-149/evidence/measurement/installed-hook-observable.json
- kaola-workflow/archive/issue-149/evidence/measurement/installed-hook-original.json
- kaola-workflow/archive/issue-149/evidence/measurement/render-check.exit
- kaola-workflow/archive/issue-149/evidence/measurement/shadow-cleanup.txt
- kaola-workflow/archive/issue-149/evidence/measurement/shadow-path.txt
- kaola-workflow/archive/issue-149/evidence/measurement/validate.exit
- kaola-workflow/archive/issue-149/evidence/measurement/verify-receipts.py
- kaola-workflow/archive/issue-149/evidence/measurement/versions-and-verdict.json
- kaola-workflow/archive/issue-149/evidence/measurement/wrapper-control-stdout.txt
- kaola-workflow/archive/issue-149/evidence/measurement/wrapper-positive-control.py
- kaola-workflow/archive/issue-149/finalization-summary.md
- kaola-workflow/archive/issue-149/mission-ledger.jsonl
- kaola-workflow/archive/issue-149/workflow-state.md
