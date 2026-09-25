# Finalization summary — issue #183

Run: dsh-KPR-i183-model-docs. Sink: merge. Branch: `workflow/issue-183`.

## Delivered

Issue #183 asked whether droid seats run the first-class Auto Model
(`modelId "auto"`, display name "Auto Model") or the CLI default promo
`gpt-5.6-sol`, on both the worker and the Host path. The run settled that
**KPR has no code defect** and delivered the documentation and test coverage
that make the reality verifiable:

1. `docs/api.md` now states that `session_meta.models.currentModelId` and
   `initial_config_options` are `session/new` snapshots that a later
   `session/set_config_option` never refreshes, and names the fields that do
   carry the current selection: `session_meta.configOptions[model].currentValue`
   (`status`/`observe`) and `effective_selection.effective_model` (`start`).
   It also records the ACP 0.225.1 protocol limitation: the protocol shows
   which model is *selected* but carries no per-turn attribution, so it cannot
   prove which model *served* a turn.
2. The droid contract suite locks the Auto Model selection from Droid's own
   `config_option_update` echo on **both** paths (worker and a Host-class name
   `droid-KPR-orchestrator-x`) and across three prompts (persistence).
3. `CHANGELOG.md` carries the Unreleased entry with `Seats: restart not
   required`, the Auto-Model-only no-substitution rule, and the mock-fidelity
   fix.

## Files Changed

| File | +/- | Why |
|---|---|---|
| `docs/api.md` | +4 | Snapshot-vs-selection field note and the protocol limitation. |
| `CHANGELOG.md` | +38 | Unreleased #183 entry, Seats line, no-substitution rule. |
| `tests/contract/test-droid-acp-contract.py` | +56 | Echo read-back helper; two-path assertions; persistence test. |
| `tests/contract/fake-droid-acp-agent.py` | +31/-8 | Mock-fidelity fix: `option_current` merges session state; echoes logged. |

No production file changed. The operator diff over
`scripts/kaola-acp-holder.py`, `scripts/kaola-zcode-acp.py`,
`scripts/kaola-quota.py`, `scripts/adapters`, and `platforms` is empty, so
running seats need no restart.

## Test Coverage

- `tests/contract/test-droid-acp-contract.py` — 16/16 OK. All three new
  assertions were each falsified against the pre-fix mock: the worker and
  Host echo assertions fail `['auto','gpt-5.6-sol'] != ['auto','auto']`, and
  the persistence assertion fails
  `['auto','auto','gpt-5.6-sol','gpt-5.6-sol','gpt-5.6-sol'] != ['auto']*5`.
- `./scripts/render-skills.py --check` — PASS, no rendered copy changed
  (`docs/api.md` is not a rendered source; render sources are `scripts/*` and
  `platforms/*.yaml`).
- `./scripts/validate.sh` — full suite green. Run with the inherited seat
  `KAOLA_*` bindings scrubbed (the #176 rule); the droid suite needs this, or
  a dispatched seat's `KAOLA_ACP_HEARTBEAT_HOST`/`KAOLA_ACP_DISPATCHER` cause
  a `heartbeat-host-conflict` refusal that the suite misreads as success
  (tracked separately as issue #182).

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- tests/contract/fake-droid-acp-agent.py
- tests/contract/test-droid-acp-contract.py

## Documentation Docking

DOCKED — `.cache/doc-docking.md`. `docs/api.md` and `CHANGELOG.md` updated;
README, architecture, conventions, host docs, API/receipt schema,
environment/setup, and examples have no impact and are recorded with reasons.
Every transcribed field name and figure was read from the live probe artifacts
or the named source line, not invented.

ACCURACY CORRECTION (recorded so it is never closed quietly): the issue body's
claims 5 and 6 ("KPR sends no model `set_config_option` at all" and "the
`resolved_model` is empty for droid") are **false**. `resolve_selection`
passes the manifest id `auto` through unchanged and the start option loop
sends `session/set_config_option model=auto`. The body's corrected evidence
comment supersedes those claims; this summary and the CHANGELOG record the
measured truth.

## Acceptance legs

| Leg | Command | Result |
|---|---|---|
| Automated (focused) | `env -u KAOLA_ACP_* python3 tests/contract/test-droid-acp-contract.py` | 16/16 OK |
| Automated (full) | `env -u KAOLA_ACP_* ./scripts/validate.sh` | exit 0, 0 FAIL |
| Render | `./scripts/render-skills.py --check` | PASS |
| Review | Claude Code review, receipt `claude-code-KPR-i183-review` | VERDICT: PASS |
| Manual/UAT | not applicable | Documentation and hermetic contract coverage only; no live seat restart required. |

## Follow-Up Items

1. **Issue #182 (pre-existing, not filed by this run):** live contract suites
   that copy the inherited environment fail from dispatched seats. Confirmed
   independently by the reviewer and re-confirmed here. The droid suite is
   green only when the seat `KAOLA_*` bindings are scrubbed.
2. **Mock-fidelity class (fixed in this run, not filed separately):** the
   `option_current` defect that masked the model is repaired in
   `tests/contract/fake-droid-acp-agent.py`. No separate issue is needed
   because the fix landed with its falsification evidence here. No other
   suite uses `option_current`.
3. The issue-quality claim correction is recorded above and will be posted as
   a closing comment so #183 does not close against text now known wrong.

## Readiness

Candidate `79f140a440ccfca1bb153f5add503aac57a3e746` is frozen, validated,
documentation-docked, and review-accepted. Ready to close #183 and sink
`workflow/issue-183` to `main` (merge sink, no PR, no release/tag/pin).

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-183/.cache/doc-docking.md
- kaola-workflow/archive/issue-183/.cache/final-validation.md
- kaola-workflow/archive/issue-183/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-183/finalization-summary.md
- kaola-workflow/archive/issue-183/mission-ledger.jsonl
- kaola-workflow/archive/issue-183/workflow-state.md
