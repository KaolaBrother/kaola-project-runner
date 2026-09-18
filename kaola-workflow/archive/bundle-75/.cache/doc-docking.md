# Documentation docking — Issue #75 (bundle-75)

Candidate: c96e605b5bde5589a71a64f15b6bc4ff26120970 (workflow/bundle-75).
Verdict: DOCKED.

## Changed public behavior vs doc checklist

| Change | Required doc | Status |
|---|---|---|
| New `scripts/kaola-codex-compact-hook.py` (prepare/install/bind/uninstall/status) — project-local `.codex/hooks.json` Host-bound `SessionStart(compact)` recovery | `docs/codex-host.md` | DOCKED — install/two-phase bootstrap, trust+review semantics, containment/dangerous-root refusals, status echo-safety, no-backup boundary all documented through review rounds |
| ZCode compact-recovery carrier (no native hook exists) — durable owner-authorized AGENTS block + per-send fallback | `docs/zcode-host.md` + generated `skills/kaola-project-runner/references/zcode-compact-recovery.md` | DOCKED — template is source of truth, rendered via render-skills.py; verdicts (manual/auto/mock-verified, real-GLM auto unverified) recorded honestly |
| Project Runner documentation-maintenance boundary | generated `skills/kaola-project-runner/references/doc-maintenance.md` (template `templates/orchestrator/references/doc-maintenance.md`) | DOCKED — policy in generated reference; main SKILL.md carries pointer only |
| User-visible feature summary | `CHANGELOG.md` | DOCKED — Issue #75 entry records hook, binding, containment, status safety, and ZCode carrier verdicts |
| Doc index / entry links | `docs/README.md`, `README.md` | DOCKED — both list codex-host.md + zcode-host.md; README links both at lines 152–153 |

## No-impact items

- APIs: no public API/schema change (new script only; receipts documented in codex-host.md).
- Setup/install: `install-local.sh` unchanged; hook install is an explicit per-project operator step, documented.
- Architecture: no new component (script + reference docs only); no registry/daemon/gate added.
- Examples: no example flows changed; consuming-project AGENTS block remains an opt-in template snippet inside the reference, not auto-applied.
- Environment: no env requirements changed.

## Checked files

README.md, CHANGELOG.md, docs/README.md, docs/codex-host.md, docs/zcode-host.md,
templates/orchestrator/references/{doc-maintenance.md,zcode-compact-recovery.md},
templates/orchestrator/SKILL.md.tmpl, generated skills/kaola-project-runner/*.

DOCKED.
