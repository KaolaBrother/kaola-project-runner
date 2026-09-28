# Documentation Docking — issue #214

## Public behavior reviewed

The issue changes the Codex Luna profile description, how local profile choices are disclosed from installed runtimes and Runner-declared presets, and the Codex computer-use selection rule. The public documentation covers those changes in README.md, CHANGELOG.md, the generated profile catalog, worker profile guidance, QA evidence guidance, and Kaola-Delegator host and handoff guidance. Source wording remains in platforms/codex.yaml and the existing templates; generated Skills were synchronized by the renderer.

## Documentation checklist

- README and catalog: updated and retained as the full supported catalog, distinct from machine-local choices.
- Profile and handoff guidance: updated for installed-only local rows, current authorization, and Sol-first/Luna fallback selection.
- Changelog: records the profile wording change and Seats: restart not required.
- Setup, APIs, architecture, environment, validation instructions, and examples: no impact; the issue adds no setup or API behavior and uses existing survey, Runner, and receipt mechanisms.
- Generated platform and Skill outputs: synchronized from their existing sources and covered by render and generated-surface validation.
- docs/harness-acp-compat-2026-09-25.md and docs/harness-acp-compat-2026-09-26.md: protected local documents; excluded from this change and left in place.

DOCKED
