# Documentation Docking

status: DOCKED

## Checked surfaces

- `docs/poc-acp-transport-2026-09-11.md`: new PoC report; all receipts quoted are
  real command output captured during the run (no invented fields).
- `docs/README.md`: PoC report indexed next to the v2 design doc.
- `README.md`: PoC report added to the live-evidence list (Chinese convention).
- `CHANGELOG.md`: Unreleased entry describes the prototype ACP transport as
  PoC scope — not wired into manifests/installer — and points at the report.
- `docs/runner-v2-dual-transport-design.md`: unchanged; the report records where
  live evidence differed from design expectations (permission gating, Grok's
  missing `agentInfo`/`usage_update`, `session_info_update` variant).
- `docs/architecture.md`, `docs/api.md`, `docs/conventions.md`: no production
  surface changed — the PoC files are prototypes outside the generated
  Skill/manifest/installer path, so no edits required.
- `AGENTS.md`: project snapshot still accurate; PoC adds no new commands to the
  documented command list.
- `templates/grok-golden/`: untouched, frozen as required.
- `skills/`: regenerated output unchanged (`render-skills.py --check` PASS).

## Fixes and no-impact findings

- Added the PoC report links to `docs/README.md` and `README.md`, and the
  Unreleased `CHANGELOG.md` entry, at commit `71eb800`.
- No public API change: `kaola-tmux.sh`, adapters, manifests, templates, and the
  installer are byte-identical to `main`.
- New environment overrides exist only on the PoC prototype:
  `KAOLA_ACP_RECORD_ROOT`, `KAOLA_ACP_COMMAND`, `--command` — documented in the
  PoC report and file docstrings.

DOCKED
