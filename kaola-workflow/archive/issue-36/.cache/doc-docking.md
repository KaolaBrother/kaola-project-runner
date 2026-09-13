# Documentation Docking — issue-36 (issue #36)

verdict: DOCKED
candidate: workflow/issue-36 @ d948b90 (post-#33+#34 merges; CHANGELOG/README/
api.md conflicts resolved preserving all entries — #34 two-tier model table
with neutralized `Skill` header, #33 configOptions paragraph, #36 installer
wording)

## Checked files

- `README.md` — UPDATED: runtime-neutral Agent Skills framing; consuming-runtime
  vs target-platform terminology; install matrix (`--runtime`, `--skills-dir`,
  `--method link|copy`, `--bin-links`); authenticated-tested vs standard-format
  compatibility distinction; neutral validation section.
- `docs/architecture.md` — UPDATED: product boundary and installer paragraph for
  runtime-aware destinations and copy/link modes.
- `docs/api.md` — UPDATED: full installer contract (flags, exclusivity, receipts,
  ownership/refusal rules, scoped uninstall, helper-link behavior).
- `docs/conventions.md` — CHECKED, no change needed: conventions unaffected by
  runtime-neutral wording and installer flags.
- `docs/README.md` — CHECKED, no change needed: index remains accurate.
- `AGENTS.md` — UPDATED: managed-region purpose/install lines neutralized
  (runtime-neutral Skills; install command unchanged in form).
- `CHANGELOG.md` — UPDATED: Unreleased entry describing issue #36 (runtime-neutral
  payload, installer contract, neutral validator, portability tests).
- `templates/SKILL.md.tmpl`, `templates/references/*.tmpl` — UPDATED: neutral
  invocation examples resolving `"$SKILL_DIR/scripts/runtime-tmux.sh"`;
  spaces-safe and outside-checkout usage documented inline.
- `platforms/*.yaml` — UPDATED: descriptions neutralized to "controlling Agent"
  wording; Codex target facts retained where legitimate.
- `agents/openai.yaml` — NO-IMPACT: retained as optional Codex display metadata
  by design.
- `templates/grok-golden/` — NO-IMPACT: frozen; byte-identical
  (`git diff -- templates/grok-golden` empty).
- `skills/` — GENERATED via `render-skills.py --write`; `--check` PASS; never
  hand-edited.

## No-impact reasons

- #33 observation wording and #34 model tier/Fast defaults on main preserved;
  no stale defaults introduced. Final integrated validation and any
  regeneration on the integrated base follow accepted #33/#34 merges.
- Historical dated records retain their original wording as dated records.
