# Document docking of issue #404
- format: kpm.workflow-doc-docking/1.0
- issue: 404

## Impact
- CHANGELOG.md | `## Unreleased` entry `Fixes #404` added: it records that `state migrate` now tolerates a present, nonempty legacy object or array `evidence` on a settled decision (the row is removed like the string case and named in `removed`), that missing/null/empty evidence, a record type problem and a foreign owner still block, that `state update --kind decisions` keeps its closed shape, and `Seats: restart not required` — the changed `cleanup_current` runs only inside the per-call `state` CLI, so a running holder's pinned projections never reach it and the fix applies on the next `state migrate` call after install. No README or `docs/` text describes this acceptance rule, so no other document is affected.

## Docking
