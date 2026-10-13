# Finalization summary — issue-310

## Delivered

Fix for #310: recovery alerts clear when a later verified checkpoint
covers them, and a partial checkpoint names its specific missing
sources.

- `scripts/kaola-record-contract.py`: `superseded_returned_inputs` — a
  returned maintenance input is settled when a later verified
  checkpoint's host-revision range covers its originating revision, or
  when its recovery request is verified satisfied (even above the
  batch range). Uncovered inputs stay.
- `scripts/kaola-acp-holder.py`: the carrier stops carrying covered
  `recovery_alerts` to new batches even when the state-file row still
  exists (the row's lifecycle stays owned by the state tool); the
  every-beat reminder for recovery#76-class stale alerts ends.
- `scripts/kaola-dispatch.py` + checkpoint records: a `partial`
  checkpoint names each unsettled input's reason —
  `recovery-sources-empty`, `not-in-batch`, `unaccounted` — the same
  vocabulary the KPM Host's own diagnosis used, surfaced in the record
  and to the Host.
- Tests: `test-issue-255-lifecycle-state.py` (+230): verified
  checkpoint clears covered inputs and keeps uncovered; holder omits a
  covered recovery alert even when the row remains; a verified recovery
  request clears its input even above the range; partial names
  empty-recovery-sources; partial names not-in-batch and unaccounted;
  the Host sees the named missing sources.
- `docs/api.md` (+24); CHANGELOG Unreleased — Seats: restart required
  (holder + record contract changed).

## Candidate

- Implementation commit `af0731b5` on `workflow/issue-310` (worktree
  `.kw/worktrees/issue-310`, base `8b9ea8c5`). Implemented by the
  `grok/default` seat `grok-KPR-i310-alerts`; reviewed and finalized by
  the Host.

## Evidence

- Host diff review (this run): clearing rule is exactly
  coverage-or-satisfaction with a stay-uncleared negative test; the
  partial vocabulary matches the KPM evidence (recovery#76/#80, batch
  b-cb80e71acb90).
- `./scripts/render-skills.py --check` — PASS.
- Affected suites, all exit 0: `test-issue-255-lifecycle-state.py`
  (updated), `test-issue-302-delegator-wake-gate.py`,
  `test-issue-299-delegator-webhook.py`,
  `test-zcode-heartbeat-contract.py`, `test-issue-271-dispatch-help.py`
  (logs `/tmp/kpr-i310-*.log`).
- `.cache/final-validation.md`: verdict `pass`, candidate hash
  `805ad3dabcc2600a…`.
- Worker seat exact-stopped after acceptance (`state: stopped`).

## Known failures / unverified scope

- Full inventory after the last of the four issues (#309 still in
  flight). No release or install in this run (owner approval
  required).

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
- scripts/kaola-dispatch.py
- scripts/kaola-record-contract.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-record-contract.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-record-contract.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-record-contract.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-record-contract.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-record-contract.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-record-contract.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kaola-project-runner/scripts/kaola-record-contract.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- tests/contract/test-issue-255-lifecycle-state.py

## Follow-Up Items

- KPM mirror comment on KaolaBrother/kaola-project-manager#138 after
  merge (owner instruction: comment only).

## Final readiness

Ready: candidate reviewed, affected scope green, validation recorded.
Proceed to sink (merge) and archive.
