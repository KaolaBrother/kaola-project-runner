# Finalization Summary — Issue #397

## Delivered

Issue #397 closes the three hard-stuck state retire/migrate paths. Candidate `68775f83` on
`workflow/bundle-397`; base `2330fe3e`.

- **One size gate with an executable local outlet.** `state migrate --write` no longer writes a
  carrier-less file above the 64 KiB legacy bound that later ordinary writes refuse. Every write
  uses the recorded `heartbeat-state/2` carrier or that legacy bound; only an owner stop keeps the
  current-bound exception. A `carrier-limit` refusal names the exact recovery:
  `state migrate --file FILE --live LIVE --write`, with `LIVE_JSON` taken from
  `kaola-acp.py list --repo ROOT --include-dead`; the recovered file records the carrier and later
  writes use 1 MiB.
- **v1 `body.alerts` (dict and list) migrates row by row** into `state.alerts` with per-row ids and
  `rev 1`. Unknown fields remain nameable `unverified` locators; their keys derive from the migrated
  alert id and disambiguate collisions, so old keys such as `a` and `a]` keep both original locator
  texts and can be named and removed by `state retire`.
- **A stopped-collect reconciliation route.** `fingerprint-differs` rows whose collected proof is
  `outcome: stopped` with `mutation_status: unknown` (a later turn killed by quota throttling or a
  similar failure) retire on `stopped-collect-incomplete-turn` under the same evidence as the strict
  continuation: Host writer only, accepted-done task, accepted per-item disposition, matching
  repo/holder/session, the row platform on every live row, and every live row stopped under the
  holder. It reports the reconciliation without rewriting the unknown index bytes.

The independent astra review returned FAIL on candidate `a6185895` for F1 (alert locator collision)
and F2 (writer/platform evidence gap); commit `68775f83` repairs both, and the Host accepted that
tip. `tests/contract/test-issue-397-retire-deadlocks.py` (27 cases) covers all three shapes, their
refusal boundaries, the collision regression, and the copied production `i398-fix` row. The
`#255`, `#259`, `#354`, `#372`, `#395`, `#286`, `#362`, `#309` and `#298` suites remain green for
the affected surfaces. Docs and the generated Skill lifecycle reference are synchronized; no
`templates/grok-golden/`, KPM, install, tag or release work was performed.

Candidate: `68775f83` on `workflow/bundle-397`; base `2330fe3e`. This run performed no tag,
release, publish, install, or KPM-side operation.

## Acceptance Evidence

- Host acceptance: F1/F2 repairs at `68775f83` were independently rechecked; F1 keeps both alert
  locators, F2 refuses all three variants with unchanged state, and the repaired shape-3 probe
  succeeds again.
- Independent astra review: `a6185895` FAIL (F1/F2), repair `68775f83` verified; review evidence is
  `/tmp/kpr397rev/REVIEW.md`.
- `tests/contract/test-issue-397-retire-deadlocks.py`: 27/27 PASS on `68775f83`.
- Focused validation on `68775f83`, exit 0, 10 suites / 344 counts (342 pass, 2 skipped, total wall
  171.932 s): `./scripts/validate.sh --suite test-issue-397-retire-deadlocks --suite
  test-issue-372-stale-collect-retire --suite test-issue-395-alert-direct-retire --suite
  test-issue-286-retire-input --suite test-issue-362-versionless-retire --suite
  test-issue-309-recovery-routes --suite test-issue-255-lifecycle-state --suite
  test-issue-259-record-contract --suite test-issue-354-state-bloat --suite
  test-issue-298-absent-decision-retire`. Log: `/tmp/kpr397fix/validate-fix.out`.
- Reviewer's four probes rerun under a clean `KAOLA_*` environment with post-fix expectations:
  alert-locator-collision keeps both locators; sideagent, foreign-platform and missing-platform all
  refuse with the route named, task retained, and index bytes unchanged. Output:
  `/tmp/kpr397fix/fixed-run-postcommit.log`.
- Pre-fix counter-proof on a base `2330fe3e` archive: the three positive shape cases fail
  (2 errors, 1 failure); output `/tmp/kpr397/prefix-counterproof.txt`.
- `./scripts/render-skills.py --check`: PASS (11 workers + orchestrator + delegator + Grok Bot
  bridge; budgets OK). Generated copies were refreshed with `--write` before the check.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- docs/conventions.md
- docs/ddd/packs/c4-state-retire.md
- docs/dispatch-collect.md
- scripts/kaola-dispatch.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/lifecycle-state.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/references/lifecycle-state.md
- tests/contract/fixtures/issue-397/i398-fix-row.json
- tests/contract/test-issue-255-lifecycle-state.py
- tests/contract/test-issue-259-record-contract.py
- tests/contract/test-issue-397-retire-deadlocks.py

## Known Failures and Unverified Scope

- No full-inventory `./scripts/validate.sh` run: the selected suites cover the changed migration,
  size gate, retire routes, lifecycle state and adjacent retire surfaces.
- No live platform ACP UAT was run for this change; it exercises the local dispatch/state CLI and
  contract fixtures, not a production Host restart.
- F2 deliberately aligns the new route with the strict continuation (Host writer and platform
  equality); the narrower permissive variants from the review are refused and tested, not allowed.

## Follow-Up Items

- No follow-up issue was filed by this run.

## Readiness

Ready for the merge sink. The candidate is committed on `workflow/bundle-397`, acceptance and
validation are recorded, and there is no tag, release, publish, install or KPM-side operation in
this run. Seats: restart required.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/bundle-397/.cache/final-validation.md
- kaola-workflow/archive/bundle-397/.cache/origin/selection-record.json
- kaola-workflow/archive/bundle-397/finalization-summary.md
- kaola-workflow/archive/bundle-397/mission-ledger.jsonl
- kaola-workflow/archive/bundle-397/workflow-state.md
