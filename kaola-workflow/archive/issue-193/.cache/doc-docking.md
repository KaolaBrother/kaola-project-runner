# Documentation Docking — Issue #193

Status: DOCKED

Checked against `AGENTS.md`'s documentation checklist for the changed installer behavior (`--runtime droid` destination, retired-root withdrawal, legacy-referrer attribution) at candidate `a94bbad9dac3331e0c021eb52f043152b0514970`.

| Surface | Decision | Reason |
|---|---|---|
| `scripts/install-local.sh` `--help` | Updated | droid row names `$HOME/.agents/skills` and the retired `~/.factory/skills` withdrawal rules; dsh and kimi-cli rows (lines 52, 102) name droid as a sharer of `~/.agents/skills`. Checked by running `--help` under a throwaway HOME. |
| `README.md` | Updated (lines 419, 477 only) | droid install example and the kimi-cli shared-root wording (shared with dsh and droid). No other README text touched; #195 owns broader README changes. |
| `docs/api.md` | Updated | Installer mapping (droid → `$HOME/.agents/skills`), Issue #193 retired-root paragraph, Kimi paragraph sharer list, pre-ledger receipt rule (`kimi-cli,dsh` for the shared root, `droid` for the retired root). The #192 quota paragraph is untouched. |
| `CHANGELOG.md` | Updated | One Unreleased entry. No release is made, so no `Seats:` line is due; the installer is not in the seat operator test paths. |
| `templates/orchestrator/references/host-entry-matrix.md`, `docs/host-entry-evidence.md` | No change | They record measured discovery roots (droid: `~/.factory/skills`, `~/.agents/skills`), which are unchanged facts. |
| `scripts/kaola-acp.py` `HOST_SKILL_DISCOVERY_DIRS` / generated `skills/` | No change | droid already lists `.agents/skills`; no template changed, and `render-skills.py --check` passes. |
| `AGENTS.md`, `docs/conventions.md`, architecture docs | No change | Commands, validation policy, architecture, and release conventions are unchanged. |
