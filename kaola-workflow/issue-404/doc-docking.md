# Document docking of issue #404
- format: kpm.workflow-doc-docking/1.0
- issue: 404

## Impact
- CHANGELOG.md | `## Unreleased` entry `Fixes #404` added: it records that `state migrate` now tolerates a present, nonempty legacy object or array `evidence` on a settled decision (the row is removed like the string case and named in `removed`), that missing/null/empty evidence, a record type problem and a foreign owner still block, that `state update --kind decisions` keeps its closed shape, and `Seats: restart required` — `scripts/kaola-record-contract.py` is in the operator restart set (`docs/conventions.md`), so a running holder keeps the previous contract until it restarts. No README or `docs/` text describes this acceptance rule, so no other document is affected.

## Docking
