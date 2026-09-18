# Issue #81 — Finalization summary

Candidate: `08dd4b5936665808e10487874c7f9912bc418843`
(`feat(zcode): native mid-turn steering via the v4 command surface (Issue #81)`),
rebased on `745668f` (origin/main after the #90 sink). Outer ACCEPT on the
pre-rebase candidate `6d0002adf7a6c4aad783283eb161ea67dd51587a` (Issue comment
5737074225); `scripts/kaola-zcode-acp.py` is byte-identical between the
accepted and rebased candidates (zero-line diff), so the accepted steering
semantics are exactly what ships.

## Delivered

- Verified installed ZCode 3.12.3 supports native mid-turn steering through
  the v4 conversation/command surface (`v4/conversation/subscribe`,
  `v4/command sendText{requestedDelivery:"guide"}`, `expectedTurnId` CAS),
  replacing the unsupported `session/steer` finding of Issue #65.
- Integrated the smallest native path into the existing `_session/steering`
  ACP method on the existing backend connection — no second lifecycle,
  scheduler, registry, retry, or stdin writer; `--steer-mode interrupt`
  remains the explicit fallback.
- Event-decided outcome ladder: `injected` only on the full same-turn
  guide-admission + drain chain with per-item `messageId` ∈
  `injectedMessageIds` and provable turn identity; queue admission →
  `not_consumed` + `mutation_performed`; silence/race/transport-loss →
  `unknown` (+`sendUncertain` where the send may have landed); explicit
  rejection → `rejected`; `-32601` → `unsupported`; idle → `promptRequired`.
- Turn-change race aborts before send (ended or backend-side successor);
  one steer-start deadline bounds every phase under the holder's 30 s;
  `BackendTransportError` separates app-server death/timeout from business
  rejection (never resent, never misreported `rejected`).
- `KAOLA_ZCODE_STEER_BUDGET` test knob is fail-safe and ≤26 s bounded —
  invalid/non-finite/non-positive input cannot crash startup or outlive
  the holder timeout.
- Sanitized live-evidence probe (`backend-tee.py` + fixture): strict
  hash-only whitelist persisted to disk (stderr→DEVNULL, unknown lines
  count-only), fixture-proven against secrets planted in every ID field.

## Files Changed

20 files, +2136/−64 vs `745668f`: adapter + holder steer mapping +
`platforms/zcode.yaml` + fake server + contract tests + CHANGELOG +
`docs/api.md` clarification + regenerated `skills/` copies.

## Test Coverage

- `test-zcode-acp-contract.py`: 71 tests (36 steer/knob legs incl. 12
  adversarial scenarios each verified red on their pre-fix SHA; raw red
  logs in `evidence/review3|4|6/`).
- Preserved: `test-issue-84` 18, `test-issue-85` 7, `test-issue-74` 151
  assertions, `test-issue-90` 19 — all green on the rebased tree.
- `evidence/live6-adapter/`: real ZCode.app 3.12.3 mid-turn `injected`
  with hash-correlated `sendText`→`steerQueued`→`steerDrained` chain and
  the model answering the steer codeword; zero raw ids/stderr/credentials
  persisted.

## Validation

`./scripts/validate.sh` — PASS, unmitigated, exit 0 on `08dd4b5`
(recorded in `.cache/final-validation.md`, code-tree hash `8baf97fa…`);
`render-skills.py --check` PASS; every suite inside the log green
including the 71-test contract and #90's 19 tests; zero residual pids.

## Changed Paths

CHANGELOG.md, docs/api.md, platforms/zcode.yaml,
scripts/kaola-acp-holder.py, scripts/kaola-zcode-acp.py,
skills/*/scripts/kaola-acp-holder.py (8 generated copies),
skills/zcode-kaola-project-runner/{SKILL.md,references/steering.md,
scripts/{kaola-acp-holder.py,kaola-zcode-acp.py,platform.yaml}},
tests/contract/{fake-zcode-app-server.py,test-zcode-acp-contract.py}.

## Documentation Docking

DOCKED — `.cache/doc-docking.md`: one real `docs/api.md` clarification
(the `not_consumed` row now notes the `steer-queued` variant); everything
else verified accurate (CHANGELOG entry, manifest summary, generated
skills re-rendered, README/zcode-host/docs README no-impact).

## Follow-Up Items

None. Every run-discovered defect was fixed in-candidate with
failure-first evidence (nine outer-review findings, all recorded in
`evidence/06-implementation-validation.md` §4a–§4g).

## Readiness

All missions done; outer ACCEPT recorded; validation green on the frozen
candidate; docs docked; sanitized live evidence archived under
`evidence/live6-adapter/`. Ready for archive → merge sink → closure.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-81/.cache/doc-docking.md
- kaola-workflow/archive/issue-81/.cache/final-validation.md
- kaola-workflow/archive/issue-81/.cache/mirror-digest.json
- kaola-workflow/archive/issue-81/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-81/evidence/01-receipt-contract-and-steer-surface.md
- kaola-workflow/archive/issue-81/evidence/02-upstream-v4-facts.md
- kaola-workflow/archive/issue-81/evidence/03-installed-3123-v4-surface.md
- kaola-workflow/archive/issue-81/evidence/04-live-v4-steering-verification.md
- kaola-workflow/archive/issue-81/evidence/05-report-and-minimal-plan.md
- kaola-workflow/archive/issue-81/evidence/06-implementation-validation.md
- kaola-workflow/archive/issue-81/evidence/adapter-delta-a7e39c2-to-0a4790e.diff
- kaola-workflow/archive/issue-81/evidence/adapter-delta-e8359e8-to-a7e39c2.diff
- kaola-workflow/archive/issue-81/evidence/candidate-01f6acc.diff
- kaola-workflow/archive/issue-81/evidence/candidate-0a4790e.diff
- kaola-workflow/archive/issue-81/evidence/candidate-67ee287.diff
- kaola-workflow/archive/issue-81/evidence/candidate-6d0002adf7a6c4aad783283eb161ea67dd51587a.diff
- kaola-workflow/archive/issue-81/evidence/candidate-8816309.diff
- kaola-workflow/archive/issue-81/evidence/candidate-a7e39c2.diff
- kaola-workflow/archive/issue-81/evidence/candidate-e09f9b9.diff
- kaola-workflow/archive/issue-81/evidence/candidate-e8359e8.diff
- kaola-workflow/archive/issue-81/evidence/live/raw-ndjson.jsonl
- kaola-workflow/archive/issue-81/evidence/live/report.json
- kaola-workflow/archive/issue-81/evidence/live2/raw-ndjson.jsonl
- kaola-workflow/archive/issue-81/evidence/live2/report.json
- kaola-workflow/archive/issue-81/evidence/live3-adapter/raw-ndjson.jsonl
- kaola-workflow/archive/issue-81/evidence/live3-adapter/report.json
- kaola-workflow/archive/issue-81/evidence/live4-adapter/raw-ndjson.jsonl
- kaola-workflow/archive/issue-81/evidence/live4-adapter/report.json
- kaola-workflow/archive/issue-81/evidence/live5-adapter/backend-evidence.json
- kaola-workflow/archive/issue-81/evidence/live5-adapter/backend-tee-config.json
- kaola-workflow/archive/issue-81/evidence/live5-adapter/backend-tee.jsonl
- kaola-workflow/archive/issue-81/evidence/live5-adapter/backend-tee.py
- kaola-workflow/archive/issue-81/evidence/live5-adapter/raw-ndjson.jsonl
- kaola-workflow/archive/issue-81/evidence/live5-adapter/repo
- kaola-workflow/archive/issue-81/evidence/live5-adapter/report.json
- kaola-workflow/archive/issue-81/evidence/live6-adapter/backend-evidence.json
- kaola-workflow/archive/issue-81/evidence/live6-adapter/backend-tee-config.json
- kaola-workflow/archive/issue-81/evidence/live6-adapter/backend-tee.jsonl
- kaola-workflow/archive/issue-81/evidence/live6-adapter/backend-tee.py
- kaola-workflow/archive/issue-81/evidence/live6-adapter/raw-ndjson.jsonl
- kaola-workflow/archive/issue-81/evidence/live6-adapter/repo
- kaola-workflow/archive/issue-81/evidence/live6-adapter/report.json
- kaola-workflow/archive/issue-81/evidence/probes/backend-tee-fixture-test.py
- kaola-workflow/archive/issue-81/evidence/probes/backend-tee.py
- kaola-workflow/archive/issue-81/evidence/probes/live-adapter-steer.py
- kaola-workflow/archive/issue-81/evidence/probes/v4-steer-probe.py
- kaola-workflow/archive/issue-81/evidence/probes/v4-steer-probe2.py
- kaola-workflow/archive/issue-81/evidence/review-fix-01f6acc-to-8816309.diff
- kaola-workflow/archive/issue-81/evidence/review-fix-67ee287-to-01f6acc.diff
- kaola-workflow/archive/issue-81/evidence/review-fix-8816309-to-e8359e8.diff
- kaola-workflow/archive/issue-81/evidence/review-fix-a7e39c2-to-0a4790e.diff
- kaola-workflow/archive/issue-81/evidence/review-fix-e8359e8-to-a7e39c2.diff
- kaola-workflow/archive/issue-81/evidence/review3/red-a7e39c2.txt
- kaola-workflow/archive/issue-81/evidence/review4/red-0a4790e.txt
- kaola-workflow/archive/issue-81/evidence/review5/adapter-delta-0a4790e-to-e09f9b9.diff
- kaola-workflow/archive/issue-81/evidence/review5/review-fix-0a4790e-to-e09f9b9.diff
- kaola-workflow/archive/issue-81/evidence/review5/tee-fixture-output.txt
- kaola-workflow/archive/issue-81/evidence/review6/adapter-delta-e09f9b9-to-6d0002a.diff
- kaola-workflow/archive/issue-81/evidence/review6/red-e09f9b9.txt
- kaola-workflow/archive/issue-81/evidence/review6/review-fix-e09f9b9-to-6d0002a.diff
- kaola-workflow/archive/issue-81/finalization-summary.md
- kaola-workflow/archive/issue-81/mission-list.md
- kaola-workflow/archive/issue-81/workflow-state.md
