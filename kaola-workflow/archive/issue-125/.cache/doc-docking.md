# Documentation docking — issue-125

verdict: DOCKED

Checked against the changed public behavior (Droid `--tier upgrade` now resolves to Auto `auto`; Kimi K3 Max `kimi-k3` at `reasoning_effort=max` is the new third tier `--tier core`, `alt_tier_label: core`; `--tier alternative` still refused):

- CHANGELOG.md — `## Unreleased` correction entry for #125 (72986ec). The #117 entry is kept as history. DOCKED.
- README.md — tier-word list gains `--tier core` on Droid; Droid preset paragraph now reads default=upgrade=Auto, core=K3 Max (72986ec). DOCKED.
- docs/api.md (:129, :485) — both Droid preset paragraphs corrected (72986ec). DOCKED.
- platforms/droid.yaml launch_summary, rendered into skills/droid-kaola-project-runner/{SKILL.md,references/platform.md,scripts/platform.yaml} (72986ec). DOCKED.
- docs/runner-v2-dual-transport-design.md (:394) — no edit: dated design record; it says default model=auto with no upgrade tier and never claims upgrade = K3 Max.
- templates/SKILL.md.tmpl third-tier sentence ("needs the same explicit user request as `upgrade`") — no edit: shared across platforms (Kimi, Devin), not Droid-specific.
- AGENTS.md, docs/architecture.md, docs/conventions.md — no impact: no new command, mechanism, or convention (reuses the #111 alt_tier_label slot).
