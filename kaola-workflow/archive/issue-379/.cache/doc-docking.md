# Documentation Docking — Issue #379

Status: DOCKED

Checked against the project documentation map for the public receipt contract.

| Surface | Decision | Reason |
|---|---|---|
| `docs/api.md` | **Updated** | Records request-scoped `mutation_performed`, false vs null, the pre-wire vs post-wire `holder-lost` distinction, `refused_busy`, start-brief failure preservation, steer companion fields, and the #383 `error.stage` forward boundary. |
| `CHANGELOG.md` | **Updated** | Unreleased #379 entry states the behavior, the post-wire death and start-brief failures, the test coverage, and `Seats: restart required` for the holder change; CLI is per-call. |
| `AGENTS.md` | No change | No command, dependency, validation policy, or project constraint changed. |
| `README.md` | No change | No setup, usage, or entry-tier behavior changed. |
| `docs/conventions.md` | No change | The existing restart/operator convention already covers the holder change; no convention text changed. |
| `templates/` | No change | No template text was needed; the 8191/8192-byte reference budgets are unchanged. |
| Generated Skill copies | Re-rendered | `./scripts/render-skills.py --write` refreshed the script copies; `--check` PASS with budgets OK. |

No new documentation docking cache is required beyond this run record.
