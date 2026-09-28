# Documentation Docking — Issue #211

Status: DOCKED

Checked against `AGENTS.md`'s documentation map and the public-behavior checklist. This recovery run changes only profile descriptions; the earlier Cursor-specific sentence and retained Grok CLI wording already landed on `ad15fc78`.

| Surface | Decision | Reason |
|---|---|---|
| `CHANGELOG.md` | Updated | Issue #211 now records both the Cursor CLI profile refinement and removal of repeated cost wording from DSH, Devin, and OpenCode, with `Seats: restart not required`. |
| `README.md` | Updated by renderer | The three affected profile rows reflect the manifests; the class and authorization sections are unchanged. |
| `skills/kaola-project-runner/references/profile-catalog.md` | Updated by renderer | The three affected catalog rows reflect the manifests, while the distinct Cursor CLI and Grok CLI rows remain byte-exact. |
| `skills/kaola-project-runner/references/worker-profiles.md` | Updated by renderer | Its three affected Worker rows are synchronized; Worker class cost/capability guidance and authorization policy are unchanged. |
| `platforms/dsh.yaml`, `platforms/devin.yaml`, `platforms/opencode.yaml` and generated `platform.yaml` copies | Updated | Only the three authorized `default_model_profile` values changed; models, classes, grants, effort, Fast settings, quotas, and concurrency are unchanged. |
| `docs/api.md`, `docs/conventions.md`, installation guidance, and architecture documents | No change | No API, transport, setup, schema, installation, or validation behavior changed. |
| `templates/grok-golden/` | No change | The frozen surface was not modified. |

No new examples or API documentation are needed. No fields or signatures were invented.
