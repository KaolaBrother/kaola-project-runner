# Finalization Summary — issue-203

## Delivered

Issue #203: launch model evidence stays available after `start`. `start` hands its existing
selection/application evidence to its holder through a new holder socket op,
`record_start_evidence`. The holder keeps it in memory as `start_evidence` and writes it on every
whole-record rewrite (`write_record`) and every `state` reply (`op_state`). `status`/`observe`
return it from the live holder, or from `record.json` when the holder is stopped or lost.

`start_evidence` holds the start receipt's existing fields, only where the receipt had them:
`model_selection`, `config_application`, `effective_selection` (for Devin, launch-argv `swe-2-max`
beside the separate `advertised_model` `swe-2-high`), `fast`, `host_selection`, `model_verified`,
`model_mismatch_reason`, `actual_runtime_model_id`, `actual_parameters`, and
`model_evidence_provenance` without its `catalog_probe`. It also records `acp_session_id`,
`resumed`, and `recorded_at`. The holder rejects evidence over 16 KiB, and `start_evidence` is
added to `STATE_BOUNDED_FIELDS`.

Evidence from a previous start is inherited only by a `--resume`/`--continue` whose adopted
`acp_session_id` equals the one in the previous record for the same platform/session/repo, and
only when that record saved its evidence under the same id. The inherited copy is labelled
`source: "prior-holder-record"` and does not nest: a resume that kept the saved model carries the
older applied evidence forward. The start receipt reports `start_evidence_recorded` and
`start_evidence_error`; neither is a refusal. These are unchanged: raw `start_selection`,
`resolve_selection`, drain-restart, and all refusals.

Issue parts → evidence (tests in `tests/contract/test-acp-contract.py`, class Issue203StartEvidenceTests):
- AC1 fresh start facts survive later holder updates → `test_fresh_start_evidence_survives_holder_rewrites` (a completed turn, then status/observe, record.json, and status after the stop).
- AC2 Devin launch-argv separate from advertised, no verified claim → `test_devin_launch_argv_stays_separate_from_the_advertised_value`.
- AC3 resume without overrides sends no model/effort config; omitted flags stay null → `test_resume_without_overrides_inherits_only_matching_evidence` (mock config calls, `start_selection.tier/model` null).
- AC4 matching evidence inherited and labelled; a reused Runner name or another native session inherits nothing → the same test, plus `test_another_native_session_under_the_same_name_inherits_nothing`.
- AC5 explicit resume override uses existing precedence; history stays separate → `test_explicit_resume_override_is_current_and_history_stays_separate`.
- AC6 old records readable; failed option application is not a refusal → `test_rejected_option_and_old_record_stay_readable_not_refusals`.
- AC7 bounded output and no credentials or transcript → 16 KiB holder limit, `STATE_BOUNDED_FIELDS`, only receipt selection fields stored (code review; Host re-read accepted).
- No registry, sidecar, history service, catalog probe, scan, or model gate → diff inspection (Host-accepted).

## Files Changed

scripts/kaola-acp.py; scripts/kaola-acp-holder.py; skills/*/scripts/kaola-acp.py and
skills/*/scripts/kaola-acp-holder.py (20 rendered copies); tests/contract/test-acp-contract.py;
docs/api.md; CHANGELOG.md. Commits d44f41ad, 84b2b5ab.

## Test Coverage

The new Issue203StartEvidenceTests pass 6/6. A mutation check showed they fail when the feature
is broken: with the client hand-off disabled all 6 fail; with the field removed from the holder's
record write 4 fail. These adjacent suites pass on the candidate:
- test-acp-contract Issue34ModelSelectionAcpTests
- test-issue-130 ModelPolicyOnAcp
- test-droid-acp-contract, test-devin-regressions, test-issue-64-receipt-bound, test-acp-holder-continue
- test-issue-162/164/165/186, test-progressive-disclosure, test-generated-skills

test-issue-119-host-entry passed 11/11 after rendering; before rendering, stale skills/ copies
caused the expected skew. `render-skills.py --write` and `--check` PASS. No live model probe was
run, and the full validate.sh was not run by scope. See .cache/final-validation.md.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- scripts/kaola-acp-holder.py
- scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- tests/contract/test-acp-contract.py

## Documentation Docking

DOCKED — see .cache/doc-docking.md.

## Follow-Up Items

None filed. Coordination note: the worker template's selection sentence (templates/SKILL.md.tmpl) may
mention `start_evidence` if the parallel #204 run chooses to; not required for #203.
Release note: scripts/kaola-acp-holder.py changed, so the next release section must say
"Seats: restart required" (already in the Unreleased entry).

## Readiness

Ready. The Host accepted 84b2b5ab. Validation passed (recorded without re-running; bytes are
unchanged). Docs are docked. The v0.6.7 tag and pin are untouched. Sink: merge into local main,
then close #203.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-203/.cache/doc-docking.md
- kaola-workflow/archive/issue-203/.cache/final-validation.md
- kaola-workflow/archive/issue-203/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-203/finalization-summary.md
- kaola-workflow/archive/issue-203/mission-ledger.jsonl
- kaola-workflow/archive/issue-203/workflow-state.md
