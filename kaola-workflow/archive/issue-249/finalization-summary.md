# Issue #249 finalization summary

## Delivered

Bounded on-demand Sidekick duty reconciliation guidance with independent
Delegator initiation through the sole Host. Recovery and pre-quiescence entries
link the new reference; the Delegator snapshot retains requirement provenance
and supports a plain-language request. Scheduling reuses existing cadence,
timer ownership and static entry, with the script-carrier option compared but
not implemented. Host alone owns state writes and completion judgment.

Candidate: `5bbbe6abecfef3b100e7d85d105e5e2ed3fd7b54`, accepted by Host.
Acceptance record: `acceptance.md`.
Evidence: `qa/validation.md`, check logs/exits, `qa/sidekick-qa.md`,
`qa/sidekick-prompt.txt`, `qa/host-acceptance-slice.json`, `qa/sidekick-stop.json`.
Sidekick loaded this candidate's guidance, checked #249 against a preserved
prior snapshot, returned the scoped result, and was exact-stopped with no
residual processes. Host accepted the check and recorded the decision in its
original state; this worker made no live snapshot changes.

Generated main Skill is 17,301/17,408 bytes (82 added, 107 remaining), new
reference 4,803/8,192, recovery reference 8,170/8,192, unchanged dispatch
reference 8,184/8,192. No ceilings changed. Normal renderer outputs include
ten main-Skill build records and content-stage bridge bookkeeping; no new
release pin, release, tag or installation. #246 wording remains outside this run.

## Documentation Impact

Guidance source entries/references and normal generated copies are the delivered
documentation. This summary, acceptance record, measured validation and changed
paths are the normal #249 finalize record; no separate documentation ledger or
release section. No extra implementation edits or candidate amendment.

## Known Failures and Unverified Scope

`./scripts/validate.sh` exits 1 at unchanged
`tests/contract/test-issue-244-dispatch.py:882`: expected `start-timeout`, observed
`status-timeout`. The isolated candidate and unchanged parent `c47daa1e` both
reproduce it. Host explicitly accepts this candidate while keeping that failure
an open observation; the assertion and dispatch code remain untouched.
Final validation recorder binds `verdict: fail` and that exact command to the
candidate. Focused renderer, budget and generated checks passed.

Bash 3.2.57 lacks Bash >= 4 `mapfile`/`BASHPID`; watchdog monitoring and two
watchdog tests have named prerequisite skips. Independent real CLI smoke per
platform was not run by this worker. The bounded Sidekick check was performed
and accepted by the Host. Wider outer personal review/retrospective and other
issues belong to their owners and remain outside this run.

## Validation

classification: final_validation_failed
green: false
mode: final-validation

.cache/final-validation.md does not record `verdict: pass` (column 0) — the agent's own validation did not pass (found verdict: fail)

.cache/final-validation.md is present but does not record `verdict: pass` (column 0). The agent's own validation did not pass — remediate and re-record, or fix the failing checks before finalize.

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-delegator/references/snapshot.md
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/duty-reconcile.md
- skills/kaola-project-runner/references/host-startup.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/grok-bot/accepted-revision.json
- templates/kaola-delegator/references/snapshot.md
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/duty-reconcile.md
- templates/orchestrator/references/host-startup.md.tmpl

## Follow-Up Items

- Open observation: the parent-reproduced #244 dispatch timeout assertion above.
  No repair, assertion change or new claim is authorized by this finalize.
  searched: GitHub open issues query `"dispatch" "timeout"`, 0 hits; no new
  follow-up issue filed because the Host explicitly retains this as an open
  observation rather than additional forge work in this #249-only finalize.
- Renderer-owned bridge/build result must remain coordinated with #247 at its
  merge time. #247 is not merged here; its worktree and implementation stay
  with its owner. No content conflict is resolved by hand in this transaction.
- #246 future shared wording must fit unchanged byte ceilings.

## Final Readiness

Host acceptance authorizes #249 close, archive, configured merge sink and
cleanup. Implementation candidate is frozen and unchanged. Lifecycle results
are determined by the transaction/sink receipts, not by this pre-sink statement.
No self-stop, release, tag, package publication or install is authorized.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-codex-160-live-2026-10-03.md
- docs/harness-acp-compat-2026-10-01.md
- docs/harness-acp-compat-2026-10-03.md
- docs/harness-acp-reverify-2026-10-01.md

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-249/.cache/final-validation.md
- kaola-workflow/archive/issue-249/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-249/acceptance.md
- kaola-workflow/archive/issue-249/finalization-summary.md
- kaola-workflow/archive/issue-249/mission-ledger.jsonl
- kaola-workflow/archive/issue-249/qa/byte-sizes.json
- kaola-workflow/archive/issue-249/qa/candidate.txt
- kaola-workflow/archive/issue-249/qa/delegator.exit
- kaola-workflow/archive/issue-249/qa/diff-check.exit
- kaola-workflow/archive/issue-249/qa/dispatch-timeout-isolated.exit
- kaola-workflow/archive/issue-249/qa/dispatch-timeout-parent-baseline.exit
- kaola-workflow/archive/issue-249/qa/generated-skills-before-scope-correction.exit
- kaola-workflow/archive/issue-249/qa/generated-skills.exit
- kaola-workflow/archive/issue-249/qa/host-acceptance-slice.json
- kaola-workflow/archive/issue-249/qa/orchestrator.exit
- kaola-workflow/archive/issue-249/qa/preserved-harness-hashes.json
- kaola-workflow/archive/issue-249/qa/progressive-disclosure-final.exit
- kaola-workflow/archive/issue-249/qa/progressive-disclosure.exit
- kaola-workflow/archive/issue-249/qa/protected-bytes-before-scope-correction.exit
- kaola-workflow/archive/issue-249/qa/protected-bytes.exit
- kaola-workflow/archive/issue-249/qa/render-check-before-scope-correction.exit
- kaola-workflow/archive/issue-249/qa/render-check.exit
- kaola-workflow/archive/issue-249/qa/render-write.exit
- kaola-workflow/archive/issue-249/qa/sidekick-prompt.txt
- kaola-workflow/archive/issue-249/qa/sidekick-qa.md
- kaola-workflow/archive/issue-249/qa/sidekick-stop.json
- kaola-workflow/archive/issue-249/qa/validate-before-scope-correction.exit
- kaola-workflow/archive/issue-249/qa/validate-delegator-skill.exit
- kaola-workflow/archive/issue-249/qa/validate-main-skill.exit
- kaola-workflow/archive/issue-249/qa/validate.exit
- kaola-workflow/archive/issue-249/qa/validation-before-scope-correction.md
- kaola-workflow/archive/issue-249/qa/validation.md
- kaola-workflow/archive/issue-249/qa/verify-generated.exit
- kaola-workflow/archive/issue-249/workflow-state.md
