# Finalization summary — issue #185

Run: droid-KPR-i185-droid-model. Sink: merge. Branch: `workflow/issue-185`.
Candidate: `d98bebe429cf22e87a52ebc0eba0d263de3455d4` (on top of `ffabe6e`).

## Delivered

Issue #185 asked that KPR's droid `model_verified` stop staying `"unknown"` and be
derived from Droid's own returned/echoed current model — the session's
current-model echo, live-probed as `auto` = "Auto Model" — without using the empty
CLI catalog or the stale `session_meta.models.currentModelId` snapshot.

1. `scripts/kaola-acp.py`: added `ECHO_VERIFIED_PLATFORMS = frozenset({"droid"})`
   and `echo_model_verification(platform, policy, effective)`, called in
   `command_start` **before** the Issue #140 launch-argv override so it reads the
   agent's raw `effective_selection` echo
   (`session_meta.configOptions[model].currentValue`). On droid it sets
   `actual_runtime_model_id` / `actual_parameters` / `model_verified` /
   `model_mismatch_reason`: `true` when the echoed model equals the resolved
   selection (echoed `reasoning_effort` compared only when the Runner pinned one),
   `false` with `actual-model-mismatch:<id>` on a mismatch, `unknown` when
   unreadable or on a preserved resume with no Runner target. Provenance
   `model_evidence_provenance.actual.source = "acp-config-echo"`. Reported
   evidence only, never a start gate. All other platforms keep `"unknown"`; their
   receipts are byte-identical.
2. `tests/contract/test-droid-acp-contract.py`: default → `true`/`auto`; core →
   `true` with `{"effort":"max"}`; explicit model → `true`; agent-rejected model
   → `false` `actual-model-mismatch:gpt-5.6-sol`; preserved resume → `unknown`
   `resume-preserved-actual-not-comparable`; and the review-required launch-argv
   test (`--command '<fake> --model auto'` whose agent echoes `gpt-5.6-sol`) →
   `actual_runtime_model_id` `gpt-5.6-sol`, `model_verified` `false`, session
   usable.
3. `docs/api.md` + `CHANGELOG.md`: the Droid-echo exception, the launch-argv
   `advertised_model` comparison rule, and `Seats: restart not required`.

### Review repair (round 2)

The Claude Code close gate returned FAIL with one blocking finding (B1): with a
launch-argv model, the Issue #140 block rewrote `effective_model` to the argv value
before the verdict read it, so droid compared the Runner's own launch value to
itself and falsely reported `true`. Fixed by moving the verdict call above the argv
override; the helper was shrunk per the smallest-form bar (unreachable
`native-default-model-not-comparable` branch deleted, comment trimmed 11 → 3
lines). The new launch-argv contract test fails with the pre-repair ordering
(`'auto' != 'gpt-5.6-sol'`) and passes after. Round 2 verdict: **PASS**.

## Files Changed

| File | +/- | Why |
|---|---|---|
| `scripts/kaola-acp.py` | +63 / −0 | Echo-verified verdict helper, pre-argv call site, provenance. |
| `tests/contract/test-droid-acp-contract.py` | +67 / −0 | Five verdict assertions plus the launch-argv test. |
| `docs/api.md` | +19 / −3 | Droid-echo exception and launch-argv comparison rule. |
| `CHANGELOG.md` | +22 / −0 | Unreleased #185 entry, Seats line. |
| `skills/*/scripts/kaola-acp.py` (10 generated copies) | +630 / −0 | Regenerated from the shared source. |

Production +63/−0, tests +67/−0, docs +41/−3; whole branch **+801/−3**. No
holder, bridge, quota-catalog, adapter, or platform file changed, so the operator
restart test is empty and running seats need no restart.

## Test Coverage

- `tests/contract/test-droid-acp-contract.py` — **18/18 OK**, including the new
  launch-argv test, which was falsified against the pre-repair ordering.
- `tests/contract/test-issue-130-pty-retired.py` (codex model-policy guarantees)
  — 49 OK; non-droid receipts unchanged.
- `tests/contract/test-issue-111-model-tiers.py` — 27 OK.
- `./scripts/render-skills.py --check` — PASS.
- `./scripts/validate.sh` — exit 0, no FAILED/SKIPPED/Traceback, 281 `... ok`.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- scripts/kaola-acp.py
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
- tests/contract/test-droid-acp-contract.py

## Documentation Docking

DOCKED — `.cache/doc-docking.md`. `docs/api.md` and `CHANGELOG.md` updated;
README, architecture, conventions, host docs, receipt schema, environment/setup,
and examples have no impact and are recorded with reasons. Every transcribed
field name and figure was read from `scripts/kaola-acp.py` or the live
`droid 0.225.1` probe receipts, not invented.

## Acceptance legs

| Leg | Command | Result |
|---|---|---|
| Automated (focused) | `env -u KAOLA_ACP_* python3 tests/contract/test-droid-acp-contract.py` | 18/18 OK |
| Automated (full) | `./scripts/validate.sh` | exit 0, 0 FAIL |
| Render | `./scripts/render-skills.py --check` | PASS |
| Live probe | `droid 0.225.1` start (no prompt) | echo `auto` → `model_verified: true`, source `acp-config-echo`; session stopped, no residual pids |
| Review | Claude Code close gate, round 2 | VERDICT: PASS |
| Manual/UAT | not applicable | Hermetic contract coverage plus a read-only live echo probe; no settings changed. |

## Follow-Up Items

1. **Issue #182 (pre-existing, not filed by this run):** live contract suites that
   copy the inherited environment fail from dispatched seats; the droid suite is
   green only with the seat `KAOLA_*` bindings scrubbed. Unchanged by this run.
2. No run-discovered defect was filed: the B1 finding was repaired inline on the
   run branch, not deferred.
3. No accuracy correction is owed: the issue body's claims (empty catalog, stale
   `models.currentModelId`, use the echo) match the measured reality.

## Readiness

Candidate `d98bebe429cf22e87a52ebc0eba0d263de3455d4` is frozen, validated,
documentation-docked, and review-accepted (round 2). Ready to close #185 and sink
`workflow/issue-185` to `main` (merge sink, no PR, no release, no tag, no pin).

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-185/.cache/doc-docking.md
- kaola-workflow/archive/issue-185/.cache/final-validation.md
- kaola-workflow/archive/issue-185/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-185/finalization-summary.md
- kaola-workflow/archive/issue-185/mission-ledger.jsonl
- kaola-workflow/archive/issue-185/workflow-state.md
