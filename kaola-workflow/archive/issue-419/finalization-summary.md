# Finalization Summary — issue-419

## Delivered

Seat stale-quota rule for Owner HARD `owner-seat-stale-quota-revoke-5h-20261028` (KPM mirror #892):

- Typed optional grant-row members `quota_stall` (5h clock) and `quota_hold` (expiry tag) in both
  durable authorization records (Host mirror `.kaola/heartbeat-prompt.json` and Delegator
  `.kaola/delegator-heartbeat.json`); schemas unchanged; closed-shape validators; migrate paths
  preserve the members; agent patches carry them forward or are refused (no forge, no strip).
- Pure `quota_verdicts` (half-open 5h window; time verdicts first) and reduce-only
  `quota_rule_apply` with the `quota-rule` writer limited to whole-row removal and member changes.
- Hooks only on existing beats: `collect` (turn_failed opens the clock, reply / `--usage`
  quota-packages envelopes are feedback), `execute`, `state check`, `delegator view`. No timer.
- Revoke removes the row like an owner revocation and writes one `quota-revoked-<preset>` warn
  alert; no auto-restore; re-add only through the existing owner grant route.
- Docs: `docs/api.md` "Seat stale-quota rule (#419)", `references/quota-packages.md`, README.

## Candidate

`workflow/issue-419` @ `3a99d328` (base `ac11d795`, v0.9.34 pin commit; bridge back to content stage).

## Acceptance

Host verdict ACCEPTED (independent re-run: grok-golden empty, live authz files untouched by the
diff, render --check PASS, test-issue-419-quota-stall 36/36, quota-rule writer typed and
removals-limited). Host decisions: V-1 accept fixed 5h hold (`until = feedback_at + 5h`);
V-2 accept login/account-refusal pause default (no clock). Both remain one-constant spots;
vendor-reset alternative documented via KPM #892.

## Evidence

- Lead recheck on final bytes: `/tmp/kpr-i419/lead-recheck.log` (419 36/36, 259, 376,
  generated-skills, progressive-disclosure OK; render --check PASS).
- Pre-review suite logs: `/tmp/kpr-i419/*.log` (255, 295, 296, 346, 148, 218, 294, 299, 312,
  345, 348, 350 OK).
- Recorded validation: `.cache/final-validation.md`.

## Known failures or unverified scope

- `test-issue-244-dispatch.py`: 9 failures identical on clean main (pre-existing, environmental;
  `/tmp/kpr-i419/fail-244-main.txt` vs `fail-244-wt.txt`).
- Whole inventory not run (focused policy). No live seat measurement of the rule.
- Residual by design: a turn that never ends opens no clock; no holder-side limit classifier.
- Release note: `kaola-record-contract.py` is holder-pinned; the next release states
  `Seats: restart required`.

## Shared-state disclosure

This run moved the canonical checkout from detached `009376db` to `main` fast-forwarded to
`ac11d795`; the untracked `kaola-workflow/archive/issue-417/` was byte-identical to main.
The run's `workflow-state.md` vanished from the main checkout while awaiting acceptance (cause
unknown) and was restored byte-for-byte from the claim output.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- README.md
- docs/api.md
- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- scripts/kaola-dispatch.py
- scripts/kaola-record-contract.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-record-contract.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/kaola-record-contract.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-record-contract.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-record-contract.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-record-contract.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-record-contract.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-record-contract.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/hermes-kaola-project-runner/scripts/kaola-record-contract.py
- skills/hermes-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/quota-packages.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kaola-project-runner/scripts/kaola-record-contract.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/grok-bot/accepted-revision.json
- templates/orchestrator/references/quota-packages.md
- tests/contract/test-issue-419-quota-stall.py

## Follow-Up Items

- None filed. Owner V-1/V-2 answers on KPM #892 may change the two constants later.

## Final readiness

Ready: accepted, all missions done, merge sink.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-419/.cache/final-validation.md
- kaola-workflow/archive/issue-419/finalization-summary.md
- kaola-workflow/archive/issue-419/mission-ledger.jsonl
- kaola-workflow/archive/issue-419/workflow-state.md
