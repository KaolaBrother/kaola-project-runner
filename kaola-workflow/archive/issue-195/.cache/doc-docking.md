# Documentation Docking — Issue #195

Status: DOCKED

Checked against `AGENTS.md`'s documentation checklist for the changed public behavior
(default-authorized five-preset inexpensive worker pool, its exemption from the general
worker concurrency count/cap, unchanged outside-pool explicit authorization, ZCode
low-cost profile) at candidate `98942335` (product surface `1a65398d`, merge `f0561176`).

| Surface | Decision | Reason |
|---|---|---|
| `templates/orchestrator/references/worker-profiles.md.tmpl` + rendered reference | Updated | The one compact canonical list: exact five pairs, pool authorization/exemption rules, no-equalization behavior, outside-pool grants, binding/lifecycle preservation. |
| `templates/orchestrator/SKILL.md.tmpl` + rendered SKILL | Updated | Authorization paragraph, Defaults Allowed-CLIs/Count rows, heartbeat gate (`No worker authorization, no heartbeat`), Report N/M scoping (pool seats live, exempt). |
| `templates/orchestrator/references/zcode-host-dispatch.md.tmpl`, `heartbeat-skeleton.txt` + renders | Updated | Pre-start count excludes pool seats; zh skeleton mirrors pool exemption, non-pool N/M report, first-intake missing-worker-authorization gate. |
| `templates/kaola-delegator/SKILL.md.tmpl`, `references/host-platforms.md.tmpl` + renders | Updated | Extraction scopes platforms/members/counts/concurrency to outside-pool workers + stated exclusions; Delegator does not enumerate or gate the pool. |
| `platforms/zcode.yaml` + rendered zcode worker Skill | Updated | `default_model_profile` carries "Very low-cost" while keeping routine-work and weak-visual characterization; model id/effort/Fast unchanged. |
| `README.md` | Updated | Cap sentence exemption, intake authorization list pool note, presets-table pointer, heartbeat-registration wording; #193 installer lines preserved after merge. |
| `docs/architecture.md`, `docs/zcode-host.md` | Updated | Control-plane description and Host-side worker count acknowledge the pool exception. |
| `CHANGELOG.md` | Updated | One Unreleased entry; no release, so no `Seats:` line due (no holder/bridge/quota-catalog/protocol diff). |
| `templates/orchestrator/references/quota-packages.md` | No change | Owned by #192; merged upstream change inherited via merge commit only. |
| `docs/api.md`, `docs/conventions.md`, `AGENTS.md`, `docs/host-entry-evidence.md` | No change | No API, installer command, convention, or host-entry fact changed. |
| `scripts/*`, `templates/grok-golden/` | No change | No transport/holder/adapter change; golden template byte-identical. |
