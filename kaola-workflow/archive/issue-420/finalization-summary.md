# Finalization Summary — issue-420

## Delivered

Root cause: stale GPT-6 Luna pins after the catalog moved the direct-model row to Codex Terra.

- `docs/api.md`: the two direct-model mechanics examples now use `--model gpt-6.1-terra` with effort max and display name Codex Terra. Preset id and preset effort stay null.
- `tests/contract/test-acp-contract.py`: the known direct-model start is `gpt-6.1-terra --effort max` and expects display name Codex Terra. Preset id, effort, and components stay null. Requested effort max is applied. An unknown model id still applies with display name null.
- `tests/contract/test-issue-244-dispatch.py`: admitted receipts use catalog `gpt-6.1-terra` / effort high. The one effort override stays max so it still differs from the catalog high. Intentional mismatches stay.
- No assertion was weakened. Hermes behavior is untouched.
- `scripts/kaola-acp-holder.py`, `scripts/kaola-compact-recovery.py`, and `templates/grok-golden/` are unchanged. `render-skills.py --write` then `--check` left `skills/` and `hosts/grok-bot/` unchanged.

## Candidate

`workflow/issue-420` @ `810f12ce910293663297bfc0cbf41a7d4bff0e14` (doc-docking) on implementation `d5392ea72b0c7972be1f8dbd28ebc21bc08bcc1c`, base `4b94a4707b8bbe4994b6478c8699bc55785f81d1`.

## Acceptance

Host verdict ACCEPTED. Verified independently on this branch (`d5392ea7` + `810f12ce`): render --check PASS, test-acp-contract.py 89 OK, test-issue-244-dispatch.py 80 OK, test-issue-416-hermes-acp.py 21 OK. Guards clean. The pre-existing #298 split collision was confirmed and left unchanged.

## Evidence

- Recorded validation: `.cache/final-validation.md` (verdict pass, hash `8e659c06671af043e8f6233cdc5ae708c8291b70054ff5f2f604ee3c51ed90a2`, bound to the worktree at `810f12ce`).
- Command: `./scripts/render-skills.py --check && ./scripts/validate.sh --suite test-acp-contract.py && ./scripts/validate.sh --suite test-issue-244-dispatch.py && ./scripts/validate.sh --suite test-issue-416-hermes-acp.py`.
- This run's earlier results on the same product bytes: render --write/--check exit 0; acp-contract 89 OK; issue-244 80 OK; issue-416 21 OK.
- Doc-docking: `kaola-workflow/issue-420/doc-docking.md` at `810f12ce`.

## Known failures or unverified scope

- Pre-existing, left unchanged: `tests/contract/test-issue-298-absent-decision-retire.py` splits the changelog on `## 0.9.3`, which also matches `## 0.9.34`, so the unreleased slice drops the #298 bullet. Observed this run (1 failed of 7). Not introduced here. Host: trivial follow-up for the next content pass, noted in the closure, not filed.
- Focused suites only. The whole inventory was not run.
- No release, tag, or install.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- docs/api.md
- tests/contract/test-acp-contract.py
- tests/contract/test-issue-244-dispatch.py

## Follow-Up Items

- Changelog split collision in `tests/contract/test-issue-298-absent-decision-retire.py` (`## 0.9.3` also matches `## 0.9.34`). Not filed. Host directed that it wait for the next content pass and be noted in the closure.

## Readiness

Ready to finalize and sink (merge).

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-420/.cache/final-validation.md
- kaola-workflow/archive/issue-420/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-420/doc-docking.md
- kaola-workflow/archive/issue-420/finalization-summary.md
- kaola-workflow/archive/issue-420/mission-ledger.jsonl
- kaola-workflow/archive/issue-420/workflow-state.md
