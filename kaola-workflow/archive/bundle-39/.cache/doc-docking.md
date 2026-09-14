# Doc docking — bundle-39 (issue #39)

Status: DOCKED

Checked files against changed public behavior:

- `docs/api.md` — UPDATED: transport paragraph now documents `holder_instance_id` minting/exposure
  points, `--expected-holder-instance-id` on permit/cancel/key-escape, the `holder-instance-mismatch`
  error shape, zero-write guarantee, omitted-flag legacy behavior, and the Runner-envelope boundary.
- `docs/acp-watch/list-view.md` — UPDATED: `holder_instance_id` row added to `kaola-acp-list/1` row
  table (string|null for legacy records) and `kaola-acp-view/1` key table; sample JSON carries the field.
- `docs/acp-watch/permit-lock.md` — UPDATED: #39 addendum records the optional binding enforced at
  the same settlement lock.
- `tests/contract/fixtures/kaola-acp-view-1.sample.json` — UPDATED: `holder_instance_id` in the frozen
  decode fixture Terminal copies.
- `CHANGELOG.md` — UPDATED: Unreleased entry; v0.1.0 section untouched.
- `README.md` — NO IMPACT: no user-facing command surface documented at flag level there.
- `templates/references/acp.md.tmpl` / generated `skills/*/references/acp.md` — checked: ACP reference
  text describes the ops surface generically; no flag-level enumeration to dock.
- `docs/runner-v2-dual-transport-design.md`, `docs/poc-acp-transport-2026-09-11.md` — historical design
  records, not living API docs; no retroactive edit.
- `templates/grok-golden/` — frozen, untouched.
