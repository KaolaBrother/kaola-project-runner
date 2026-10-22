# Document docking of issue #405
- format: kpm.workflow-doc-docking/1.0
- issue: 405
- candidate: 86a42506967753bdebee74d61cc32e766bbd1dde
- checked_by: host
- checked_at: 2026-10-23T07:45:00Z
- verdict: docked

## Impact
- CHANGELOG.md | `## Unreleased` gains a `Fixes #405` clause in the fixes line and one bullet recording the wait-decoupling across the holder-timing suites and the gate recovery route
- docs/conventions.md | new paragraph after the slow-feedback rule: the single-suite standalone rerun receipt (`./scripts/validate.sh --suite <inventory-basename>`) as the accepted recovery for a suspected load flake, plus the stall-watchdog wait semantics and the unchanged per-suite watchdog
- scripts/validate.sh | `--help` usage text gains the same recovery route (standalone `--suite NAME` rerun on the same tree, keep both receipts, no more full-gate copies)
- README.md / docs/api.md | no change: no command surface, schema or architecture fact moved

## Docking
- CHANGELOG.md | updated — `Fixes #405` clause and bullet present in `## Unreleased`; Host review repair corrected the wording (watchdog scope is the probed surfaces only, socket traffic is not probed)
- docs/conventions.md | updated — recovery-route paragraph present; corrected watchdog scope wording applied in the repair round
- scripts/validate.sh | updated — `--help` usage carries the recovery route
- README.md / docs/api.md | no-impact — no command surface, schema or architecture fact moved; confirmed by the repair round's scope
