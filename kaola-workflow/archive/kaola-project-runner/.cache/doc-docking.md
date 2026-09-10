# Documentation Docking

status: DOCKED

## Checked surfaces

- `README.md`: documents Devin CLI in the six-platform table and quick-use examples.
- `CHANGELOG.md`: records the new Devin Runner behavior under Unreleased, including the current
  `auto` permission default, direct transport, model/session evidence, and exact resume/stop support.
- `docs/api.md`: documents six generated Skills, the `devin` installer platform ID, and
  `DEVIN_BIN`.
- `docs/architecture.md`: documents the six-platform generated architecture and Devin session
  ownership.
- `docs/conventions.md`: documents the shared six-platform active template boundary.
- `AGENTS.md`: records verified purpose, stack, architecture, commands, security boundary,
  compatibility constraints, generated surfaces, and validation policy.
- `skills/devin-kaola-project-runner/SKILL.md` and `references/platform.md`: generated public Runner
  instructions match the current adapter behavior: Adaptive model, `auto` permission mode,
  evidence-only observations, empty TUI session identifier, and exact continue/resume/stop.

## Fixes and no-impact findings

- Added the missing Unreleased entry to `CHANGELOG.md` and validated it at commit `4cf7233`.
- No public API migration, configuration migration, environment-file change, or sample project is
  required. The only new environment override is the documented optional `DEVIN_BIN`.
- `templates/grok-golden/` remains unchanged and frozen as required.
- The generated Skill surfaces were regenerated from shared templates and verified deterministic by
  `python3 ./scripts/render-skills.py --check`.

DOCKED
