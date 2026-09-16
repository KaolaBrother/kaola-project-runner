# Documentation Docking — issue-56

status: DOCKED

Changed public behavior: the Grok Bot install/UAT guide and the shared orchestrator host
reference no longer require (or mention) Settings > Plugins > Yours visibility or `/`
discovery; the attestation and worker `preflight` are stated to establish placement, not
live use. No API, CLI flag, setup step, environment, or validation command changed.

## Checked surfaces

- `CHANGELOG.md` — FIXED. Added an `Unreleased` entry for Issue #56 describing the removed
  impossible gate, the now-UI-free agent-facing surfaces, the placement/live-use split, and
  the unchanged delivery shape (one thin account Skill, no Marketplace, no second Skill, no
  new installation step). No release or tag, so `Unreleased` is the correct section.
- `docs/grok-bot-host.md` — FIXED in the run commits. Carries the corrected guidance plus the
  single `Historical note (Issue #56, recorded here only)` and the three separated evidences
  (accepted `SKILL_EXPOSURE: PASS` at `bc8592d`, attestation + read-only worker `preflight`
  for placement, separately authorized real-use smoke for live use).
- `templates/grok-bot/INSTALL.md.tmpl` and generated `hosts/grok-bot/INSTALL.md` — FIXED in
  the run commits; zero account-UI vocabulary, six steps unchanged.
- `templates/orchestrator/references/grok-bot-host.md` and generated
  `skills/kaola-project-runner/references/grok-bot-host.md` — FIXED in the run commits.
- `README.md` — no impact. Its Grok Bot section describes the bridge shape, target binding,
  locator registration, and the R/P commit pair; it contains no plugin-list or slash-discovery
  gate (`rg 'Plugins > Yours|slash discovery|/` offers'` returns no README hit).
- `AGENTS.md` — no impact. The project snapshot already describes the one thin account Skill,
  target binding, device-local locator, and the progressive-disclosure byte budgets; none of
  those facts changed.
- `docs/api.md`, `docs/architecture.md` — no impact. `rg 'Yours|Plugins|SKILL_EXPOSURE'`
  across `docs/` matches only `docs/grok-bot-host.md` lines 251 and 259-260 (the maintainer
  historical note).
- `scripts/install-local.sh`, `scripts/kaola-grok-bot-package.py` — no impact; `rg
  'Yours|Plugins'` over `scripts/` returns no match. Grok Bot still has no installer
  destination and no new install step was added.
- Examples / setup instructions — no impact; installation burden is unchanged (one native
  save, locator registration, bounded read-only preflight).

## Verdict

DOCKED. Every changed public behavior is documented; no surface still states or implies the
removed account-UI gate, and no doc claims the read-only preflight proves live use.
