# Doc docking — issue-121 (candidate a75cb23)

Checked against AGENTS.md documentation map and the changed public behavior (new Host `start`
refusal `main-skill-build-skew`, receipt fields `main_skill_build` / `main_skill_skew` /
`main_skill_skew_count`, generated file `scripts/main-skill-build.json` in every worker Skill).

- templates/orchestrator/references/host-entry-matrix.md (+ rendered skills/.../host-entry-matrix.md): FIXED — the "main Skill ships no scripts and is not compared, a same-named older copy wins" sentence now states the #121 comparison and refusal.
- templates/orchestrator/references/host-startup.md.tmpl (+ rendered): FIXED — one sentence on `main-skill-build-skew` beside `worker-skill-build-skew`.
- docs/api.md: FIXED — full contract (record format, match rule by frontmatter name incl. renamed backups, extra files ignored, receipt fields, null cases).
- docs/zcode-host.md: FIXED — residuals paragraph gains the main Skill comparison.
- CHANGELOG.md: FIXED — Unreleased entry.
- README.md: NO IMPACT — four-tier entry/usage unchanged; install commands unchanged.
- docs architecture / install-local.sh help: NO IMPACT — installer behavior unchanged (the new file ships inside the worker Skill tree it already copies).
- templates/grok-golden/: untouched (frozen).

DOCKED
