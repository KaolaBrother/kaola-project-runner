# Documentation docking — Issue #96

status: DOCKED

## Checked against the AGENTS.md documentation map

| file | verdict | reason |
|---|---|---|
| `CHANGELOG.md` | **updated** | The operator-visible effect is real: an Agent bound as a Project Runner control plane previously could not run `./scripts/validate.sh` without `env -u`. The repository already changelogs validate/test-infrastructure issues (`Issue #83` at line 432, `Issue #63` at line 759), so an `## Unreleased` entry is the consistent treatment. Entry states the test-only boundary explicitly. |
| `README.md` | no impact | Line 258 documents `export KAOLA_PROJECT_RUNNER_CANONICAL_REPO=/path/to/project` as production Orchestrator setup. The guard is unchanged, so this stays accurate; it is not a test-harness instruction and must not be weakened. |
| `docs/api.md` | no impact | Line 227 describes the binding as declaring Orchestrator context. Unchanged behavior. |
| `docs/architecture.md` | no impact | Line 231 describes the one-entrypoint guard in `scripts/kaola-tmux.sh`. Unchanged behavior. |
| `AGENTS.md` | no impact | Validation Policy names `./scripts/validate.sh` and `./scripts/render-skills.py --check`. Both remain the exact commands; the fix removes an environment precondition rather than changing a command. |
| public API / setup / environment / examples | no impact | No production file changed. Diff vs main is 2 test files, +13/-0. |

## Verified, not assumed

- No document anywhere instructs `env -u KAOLA_PROJECT_RUNNER_CANONICAL_REPO`, so there is no
  stale workaround left behind to retract: `grep -rn "env -u" README.md CHANGELOG.md AGENTS.md docs/`
  returned no hit.
- All four existing mentions of the binding describe the production guard, which this run did not touch.
