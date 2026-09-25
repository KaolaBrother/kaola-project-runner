# Documentation Docking

## Result

DOCKED

## Checked

- `CHANGELOG.md`: the existing Unreleased Issue #163 entry documents the
  platform-default permission mode, explicit and recorded mode precedence, and
  the unchanged selection refusal.
- `docs/api.md`: documents the drain-restart default mode behavior and the
  refusal gate's complete start-selection inputs, including `--mode`.
- `README.md`: checked; no change needed because this is an ACP API behavior
  detail, not a new user-facing workflow or installation path.
- `docs/conventions.md` and architecture documentation: checked; no change
  needed because the transport and lifecycle architecture is unchanged.
- Generated worker Skills: covered by the repository render and validation
  checks; no hand edits were made to generated output.

## Evidence

- Candidate: `b73626bebf553ca154f5ad2c0ecec18e39114333`
- Validation: `./scripts/validate.sh`, exit 0
