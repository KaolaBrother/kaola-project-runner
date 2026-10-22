# Finalization Summary — Issue #387

## Delivered

Issue #387's prompt provenance is nameable end to end on `workflow/issue-387`.

- `add_user_from_prompt` accepts a source (`delegator` or `self`) and an optional carrier
  schema id. The prompt message row and its turn row store the facts internally; `snapshot`
  publishes `prompt_source` on the prompt's `messages[]` user row, `source` on its `turns[]`
  row, and `carrier` only when a carrier schema is known. `kaola-acp-view/1` is unchanged;
  these are additive optional fields.
- A normal `turn_ended` event carries `prompt_source`, matching the agent-initiated precedent.
  `record.last_prompt.source` is written on admission, a failed write, turn end and agent exit,
  so a reconnected holder can still attribute the last prompt.
- `op_steer_interrupt` follow-ups record their own Delegator origin and never inherit the
  cancelled turn's source or carrier, per the documented matrix.
- Socket entry points strip the internal `_prompt_source`/`_prompt_carrier` markers, so a wire
  client cannot claim holder-internal provenance.
- The worker-event carrier passes `kaola-host-notify/1` (Host) or `kaola-worker-notify/1`
  (non-Host).
- The frozen view spec `docs/acp-watch/list-view.md`, `docs/api.md`, `CHANGELOG.md`, the sample
  fixture and the generated Skill copies are updated.
- `tests/contract/test-issue-387-prompt-source.py` (16 cases) covers both sources end to end,
  the carrier id, the steer matrix (including an agent-initiated target), the socket strip, the
  fixture, and two pre-fix counter-proof classes. It is registered in `scripts/validate.sh`.

Candidate: `81b8e238` on `workflow/issue-387`; base `1e49d8df`. This run performed no tag,
release, publish, install, or KPM-side operation.

## Acceptance Evidence

- Host acceptance passed, followed by an independent astra review PASS: 105/105 review checks,
  10/10 probes, and two mutation detections.
- Final tip validation, exit 0, on `81b8e238`:
  `./scripts/validate.sh --suite test-issue-387-prompt-source.py --suite test-issue-381-view-snapshot.py --suite test-issue-385-view-echo-dedupe.py --suite test-acp-watch-contract.py --suite test-acp-follow-contract.py --suite test-issue-341-agent-initiated-turn.py`
  - `test-issue-387-prompt-source.py`: 16/16 OK, 4.414 s.
  - `test-issue-381-view-snapshot.py`: 18/18 OK, 6.893 s.
  - `test-issue-385-view-echo-dedupe.py`: 30/30 OK, 2.326 s.
  - `test-acp-watch-contract.py`: 20/20 OK, 23.304 s.
  - `test-acp-follow-contract.py`: 12/12 OK, 20.433 s.
  - `test-issue-341-agent-initiated-turn.py`: 9/9 OK, 29.172 s.
  - Total wall 67.141 s; no residual pids. Log: `/tmp/kpr387-final-focused-tip.log`.
- `./scripts/render-skills.py --check`: PASS (11 workers + orchestrator + delegator + Grok Bot
  bridge; content stage; budgets OK). `render-skills.py --write` was run before the check.
- Broader affected set, exit 0, 18 suites: the six above plus
  `test-issue-384-view-disclosure.py`, `test-acp-contract.py`,
  `test-issue-380-client-message-id.py`, `test-issue-65-steering.py`,
  `test-issue-65-steer-race.py`, `test-issue-263-steer-adaptation.py`,
  `test-issue-302-delegator-wake-gate.py`, `test-issue-392-host-turn-done-wake.py`,
  `test-issue-388-role-carrier.py`, `test-issue-393-cwd-carrier.py`,
  `test-issue-259-record-contract.py`, `test-issue-64-receipt-bound.py`.
  Log: `/tmp/kpr387-affected-3.log`.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/acp-watch/list-view.md
- docs/api.md
- scripts/kaola-acp-holder.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- tests/contract/fixtures/kaola-acp-view-1.sample.json
- tests/contract/test-acp-follow-contract.py
- tests/contract/test-acp-watch-contract.py
- tests/contract/test-issue-387-prompt-source.py

## Known Failures and Unverified Scope

- No full-inventory `./scripts/validate.sh` run: the selected suites cover the changed holder
  provenance path, the view/follow contracts, the steer paths, the record contract and the
  adjacent carrier suites.
- The live contract probes use the repository's mock ACP agent with a real holder; no external
  platform vendor UAT was run, and no real platform binary was exercised for this change.
- `prompt_source`/`source` are absent on a legacy `record.last_prompt` written before this
  change; that is unknown, not inferred.

## Follow-Up Items

- No follow-up issue was filed by this run.

## Readiness

Ready for the merge sink. The candidate is committed on `workflow/issue-387`, acceptance is
recorded, and there is no tag, release, publish, install or KPM-side operation in this run.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-387/.cache/final-validation.md
- kaola-workflow/archive/issue-387/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-387/finalization-summary.md
- kaola-workflow/archive/issue-387/mission-ledger.jsonl
- kaola-workflow/archive/issue-387/workflow-state.md
