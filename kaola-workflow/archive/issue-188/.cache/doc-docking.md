# Documentation Docking — issue-188

Candidate: ca1a2fafdef6af44afa029acc337b7f21fd8840e (workflow/issue-188)

Checked files:
- README.md — fixed: model-selection chapter replaces the default|upgrade / fixed-alt prose with the full ten-platform table (default, every named `--tier` with model and effort, "default only" for dsh/Grok/OpenCode/ZCode), states only `default` is common, names are unranked, effort is separate (Sonnet/Luna max is not an upgrade), undeclared incl. retired `upgrade` is `tier-not-declared` (adac3c4, ca1a2fa). Checked row by row against the #188 issue table (body updated 2026-09-27T01:46:01Z).
- docs/api.md — fixed: manifest model-selection fields (`named_tiers`, `<w>_model_*`, `acp_command_<w>`), `--tier default|PLATFORM_TIER` usage, typed refusal incl. drain-restart recorded tier, Droid opus/core, Claude sonnet / Codex luna wording.
- docs/architecture.md — fixed: `--tier NAME` paragraph (only default common, `named_tiers`, retired upgrade refused).
- CHANGELOG.md — fixed: `## Unreleased` #188 bullet (operator-diff fact: every platforms/*.yaml and scripts/adapters/*.sh changes); kept alongside the #189 bullet after the merge.
- templates/orchestrator/SKILL.md.tmpl — fixed: stale "Upgrade" defaults row became "Other tiers" (57fe50b).
- templates/kaola-delegator/references/host-platforms.md.tmpl, templates/orchestrator/references/host-entry-matrix.md — no impact: generic `--tier`/`--model`/`--effort` wording, still correct.
- AGENTS.md — no impact: commands, constraints, validation policy unchanged.
- scripts/kaola-tmux.sh usage and kaola-acp.py `--tier` metavar — fixed (`default|PLATFORM_TIER`).
- skills/, hosts/grok-bot/ — generated; render-skills.py --write, --check PASS; hosts/grok-bot identical to main.
- Historical CHANGELOG release sections and dated design docs (docs/runner-v2-*) — no change: history is not rewritten.

Result: DOCKED
