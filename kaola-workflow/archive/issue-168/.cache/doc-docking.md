# Documentation Docking — issue #168

DOCKED

## Checked

- `CHANGELOG.md` — Unreleased entry for Issue #168 names all five
  `reported_drift` values, states that seat behavior is unchanged, cites
  `tests/contract/test-issue-168-drift-enumeration.py`, and carries
  `Seats: restart not required`. The operator-test path set
  (holder, ZCode bridge, adapters, platform manifests) is empty for this
  commit.
- `templates/references/acp.md.tmpl` and
  `templates/orchestrator/references/zcode-host-dispatch.md.tmpl` — the
  status paragraph and the Host dispatch `reported_drift` list now name
  pin, CLI-file, and quota-catalog drift plus a recorded script path that
  no longer exists and an install tree that moved or was re-rooted.
  Generated Skill copies were refreshed with `./scripts/render-skills.py --write`
  and `--check` passed.
- `docs/api.md` — no impact. Its existing `reported_drift` sentence already
  names `pin-drift`, `cli-drift`, `build-unrecorded`, and `checkout-drift`.
  Issue #168's accepted surfaces were the seat-stale refusal and the two
  templates, not this paragraph. The reviewed candidate is left unchanged.
- `README.md`, architecture, setup, and validation guidance — no impact.
  No new command, environment, or example.

No additional product documentation changes were needed during finalization.
