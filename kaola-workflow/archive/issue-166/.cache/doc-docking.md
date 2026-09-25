# Documentation Docking — issue #166 bundle

DOCKED

## Checked

- `CHANGELOG.md` — Unreleased entries cover Issue #166's named `quota-drift`
  report, unchanged staleness semantics, legacy-record silence, and the Issue
  #167 test rename.
- `templates/references/acp.md.tmpl` and
  `templates/orchestrator/references/zcode-host-dispatch.md.tmpl` — document
  quota-catalog drift as a non-blocking `reported_drift` condition. Generated
  Skill references were refreshed and render validation passed.
- `docs/api.md` — existing `status`/`list` field and stale-dispatch contract
  remain valid; no API shape, setup, architecture, or example changes are
  required for this additive reported-drift value.
- `README.md`, architecture/setup documentation, and validation guidance —
  no impact beyond the already-documented changelog and generated reference
  updates.

No additional product documentation changes were needed during finalization.
