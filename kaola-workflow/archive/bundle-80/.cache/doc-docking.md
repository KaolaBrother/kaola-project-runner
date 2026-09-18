# Documentation docking — Issue #80

Checked against AGENTS.md's Documentation Map: README.md, CHANGELOG.md, docs/.

| surface | verdict | reason |
|---|---|---|
| `CHANGELOG.md` | UPDATED | The repair is dev-visible: `./scripts/validate.sh` was red on a clean `main` and a whole suite lane went unreported. Entry added under `## Unreleased` in the existing per-issue voice (commit `93310eb`, finalization docking on top of the ACCEPTed `c4caf37`). |
| `README.md` | NO IMPACT | Describes project purpose and usage. No command, flag, install path, or output changed. |
| `docs/` (all) | NO IMPACT | No public signature, JSON field, help text, environment variable, budget, architecture component, or validation command changed. The fix is env/config inside one test fixture; `render-skills --check` reports budgets OK and generated surfaces are byte-identical. |
| `tests/contract/test-issue-49-grok-bot-host.py` | UPDATED | Two comments at the point of use record the measured gate facts (why `maintenance.auto`/`receive.autogc`, and that `gc.auto=0` does not gate the spawn). |

status: DOCKED
