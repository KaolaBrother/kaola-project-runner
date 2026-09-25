# Documentation Docking

## Result

DOCKED

## Checked

- `CHANGELOG.md`: the Unreleased Issue #165 bullet documents both new
  reported-only conditions by name (`recorded-path-missing` with
  `missing_files`; `install-root-mismatch` with `recorded_root` /
  `install_root`), the per-platform expected-root rule, that neither sets
  `stale` nor gates transport, and `Seats: restart not required`.
- `docs/api.md`: checked; the seat-freshness paragraph enumerates the
  `reported_drift` conditions, and the sibling drift follow-up (Issue #166,
  `quota-drift`) did not extend that enumeration either, so the repository's
  docking surface for these N-follow-ups is the CHANGELOG bullet. No change
  made, to keep the reviewed candidate bytes frozen.
- `README.md`: checked; no change needed — this is an ACP `status`/`list`
  reporting detail, not a new user-facing workflow, install path, or setup
  step.
- `docs/conventions.md` and architecture documentation: checked; no change
  needed — the holder, ZCode bridge, protocol, and transport/lifecycle
  architecture are unchanged (the operator restart test is empty).
- Generated worker Skills: covered by `./scripts/render-skills.py --check`
  and `./scripts/validate.sh`; no generated surface was hand-edited.

## Evidence

- Candidate: `c54d22e8b2fabe858fd00836c8164d85de680bd6`
- Validation: `./scripts/validate.sh`, exit 0
