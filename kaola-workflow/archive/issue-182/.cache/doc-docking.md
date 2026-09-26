# Documentation Docking — Issue #182

Status: DOCKED

Checked against `AGENTS.md`'s documentation checklist for changed public behavior.
This run is tests-only (`tests/contract/` + `CHANGELOG.md`); no production script,
generated Skill, adapter, template, or doc source changed (`render-skills.py --check`
PASS with zero generated-surface diffs).

| Surface | Decision | Reason |
|---|---|---|
| `CHANGELOG.md` | **Updated** | Unreleased entry for #182 records the user-visible effect (dispatched-seat contract loops no longer inherit the seat's `KAOLA_*` binding env, refusals now surface at the refused command), names `test-issue-130-pty-retired.py` as fixed transitively and `test-zcode-acp-contract.py`'s `KAOLA_ZCODE_*`-absent measurement, and states `**Seats: restart not required**` with an empty operator test — only `tests/contract/` files changed. |
| `docs/api.md` | No change | No receipt field, schema, error code, or protocol vocabulary changed; the change is confined to how test fixtures build spawned-command environments. |
| `docs/conventions.md` | No change | The seat-restart and operator-test conventions are satisfied by the CHANGELOG entry; the convention text itself is untouched. |
| `AGENTS.md` | No change | No command, install step, validation policy, or project constraint changed. |
| `README.md` | No change | No setup, usage, or entry-tier behavior changed. |
| `docs/architecture*.md`, `docs/zcode-host.md`, other `docs/` | No change | No production behavior changed anywhere; the suites are the covering tests for the env-hygiene and refused-check patterns. |

Public behavior documented: the CHANGELOG entry names the failing condition
(`KAOLA_ACP_HEARTBEAT_HOST` + `KAOLA_ACP_DISPATCHER` naming different holders copied from
`os.environ`), the typed refusal that error-only checks used to pass
(`result == "refused"` / `heartbeat-host-conflict`), the #176 reference pattern now applied
everywhere, and the `Seats: restart not required` operator boundary.

No invented fields, signatures, or schema were transcribed.
