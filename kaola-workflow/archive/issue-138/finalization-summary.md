# Finalization summary — issue-138

## Delivered
Grok Bot pin hygiene per the Fable design in #138: the locator's registration receipt is the
machine's one pin. `--expect-revision E` that is a proper ancestor of the registered accepted
revision adds `expect-revision-superseded` beside `revision-mismatch`; `register` refuses such an E
as `accepted-revision-superseded` before touching link or receipt. Unknown/unrelated E and
descendant E behave as before. Rollback = owner removes the receipt, then `register`. Bridge
step 2 reworded to the design's measured text (2555 B content stage); the Delegator handoff Grok
Bot co-location command drops `--expect-revision` (8163 B).

## Files Changed
scripts/kaola-locate.py; templates/grok-bot/bridge.md.tmpl; templates/grok-bot/INSTALL.md.tmpl;
templates/kaola-delegator/references/handoff.md.tmpl; generated hosts/grok-bot/{kaola-delegator.md,
bridge.json, INSTALL.md}, skills/kaola-delegator/references/handoff.md; docs/api.md;
docs/grok-bot-host.md; README.md; CHANGELOG.md; tests/contract/test-issue-49-grok-bot-host.py;
tests/contract/test-issue-74-kaola-delegator.py.

## Test Coverage
Acceptance 1-5: `Issue49LocatorAttestation.test_superseded_revisions_are_refused_both_ways_and_rollback_removes_the_receipt`
(fails on the 52fd366 locator with ['revision-mismatch'] only; passes on b2876df). Acceptance 6:
test-49 bridge text/negative assertions + pinned-stage bridge ≤ 2560 B in the pin-gate test;
test-74 check that the handoff carries no `--expect-revision`. test-49: 45 OK; test-74: 186
assertions, 0 failed. Acceptance 7 (live owner UAT on this Mac): owner-side, not executed.

## Validation
- `./scripts/render-skills.py --check` — PASS (1 bridge skill, 2555 B, content stage, budgets OK)
- `python3 scripts/kaola-grok-bot-verify.py --repo . hosts/grok-bot` — PASS (no canonical content; generated state)
- `./scripts/validate.sh` — rc=0 at b2876df, log kaola-workflow/issue-138/validate.log (653 lines, 0 FAIL/ERROR)
- `git diff --check 52fd366 b2876df` — clean
- Host acceptance: PASS (independent verification, 2026-09-22)
- Record: .cache/final-validation.md, validated_candidate_hash a9050570b9b4aa26…

## Changed Paths
- CHANGELOG.md
- README.md
- docs/api.md
- docs/grok-bot-host.md
- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- scripts/kaola-locate.py
- skills/kaola-delegator/references/handoff.md
- templates/grok-bot/INSTALL.md.tmpl
- templates/grok-bot/bridge.md.tmpl
- templates/kaola-delegator/references/handoff.md.tmpl
- tests/contract/test-issue-49-grok-bot-host.py
- tests/contract/test-issue-74-kaola-delegator.py

## Documentation Docking
DOCKED — see .cache/doc-docking.md.

## Follow-Up Items
- Acceptance 7: owner read-only live UAT on this Mac (`kaola-project-runner-locate --target local
  --expect-revision <v0.5.6 R>` → `expect-revision-superseded`; v0.5.7 R → ok). Owner-side, no issue filed.
- INSTALL.md pinned-stage render ≈ 8098/8192 B — headroom note, not a defect.
- No new defects discovered; no follow-up issue filed.

## Readiness
READY — closure decision: close #138.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-138/.cache/doc-docking.md
- kaola-workflow/archive/issue-138/.cache/final-validation.md
- kaola-workflow/archive/issue-138/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-138/finalization-summary.md
- kaola-workflow/archive/issue-138/mission-ledger.jsonl
- kaola-workflow/archive/issue-138/workflow-state.md
