# Document docking of issue #404
- format: kpm.workflow-doc-docking/1.0
- issue: 404
- candidate: cb0f43ff3d5c5673fb698ea7b6bf890707905769
- checked_by: host (record completed by the run session on Host directive; independent review claude-code-KPR-i404-review)
- checked_at: 2026-10-23T00:45:00Z
- verdict: docked

## Impact
- CHANGELOG.md | `## Unreleased` entry `Fixes #404` added: it records that `state migrate` now tolerates a present, nonempty legacy object or array `evidence` on a settled decision (the row is removed like the string case and named in `removed`), that missing/null/empty evidence, a record type problem and a foreign owner still block, that `state update --kind decisions` keeps its closed shape, and `Seats: restart required` — `scripts/kaola-record-contract.py` is in the operator restart set (`docs/conventions.md`), so a running holder keeps the previous contract until it restarts. No README or `docs/` text describes this acceptance rule, so no other document is affected.

## Docking
- D1 | CHANGELOG.md | updated | the `## Unreleased` `Fixes #404` entry exists at the candidate with the corrected migrate-only tolerance, the blocking variants, the closed-shape write path and `Seats: restart required` citing the holder pin
