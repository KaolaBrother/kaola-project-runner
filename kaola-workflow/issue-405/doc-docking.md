# Document docking of issue #405
- format: kpm.workflow-doc-docking/1.0
- issue: 405
- candidate: <filled at candidate boundary>
- checked_by: host (independent review pending)
- checked_at: <pending>
- verdict: pending

## Impact
- CHANGELOG.md | `## Unreleased` gains a `Fixes #405` clause in the fixes line and one bullet recording the wait-decoupling across the holder-timing suites and the gate recovery route
- docs/conventions.md | new paragraph after the slow-feedback rule: the single-suite standalone rerun receipt (`./scripts/validate.sh --suite <inventory-basename>`) as the accepted recovery for a suspected load flake, plus the stall-watchdog wait semantics and the unchanged per-suite watchdog
- scripts/validate.sh | `--help` usage text gains the same recovery route (standalone `--suite NAME` rerun on the same tree, keep both receipts, no more full-gate copies)
- README.md / docs/api.md | no change: no command surface, schema or architecture fact moved

## Docking
<pending acceptor>
