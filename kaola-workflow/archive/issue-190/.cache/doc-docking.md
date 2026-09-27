# Documentation Docking — issue-190

Candidate: f442ae2a8c190f16cc98cefc6f985b525f90599b (workflow/issue-190; code candidate 2795c27 Host-accepted, plus Host-accepted doc-only f442ae2)

Checked files:
- README.md — fixed (469d490, fd4cd2b): the ten-platform tier table shows Cursor `opus` `claude-opus-5-5-medium`, Devin `opus-fusion` `fusion-claude-opus-5-5-medium-sidekick-swe-2-medium`, Droid `opus` `reasoning_effort` `medium`; the model-selection section references the complete rendered profile table skills/kaola-project-runner/references/worker-profiles.md (not copied) and states the per-seat same-runtime switch grant.
- CHANGELOG.md — fixed: two `## Unreleased` #190 bullets (worker profiles and per-seat switching; Opus presets at medium) with operator-diff facts (platforms/*.yaml profile keys; cursor-cli/droid/devin platforms and adapters). No release section.
- docs/api.md — fixed (f442ae2): manifest model-selection keys list default_model_profile/<w>_model_profile (may be empty, no '|', rendered only into worker-profiles.md, never a preset change or start gate); both Droid `--tier opus` passages say reasoning_effort=medium.
- docs/architecture.md — no impact: names tier words only (`--tier opus-fusion` etc.), no efforts or profile keys.
- templates/orchestrator (SKILL.md.tmpl Other-tiers row, references/worker-profiles.md.tmpl), templates/kaola-delegator/references/host-platforms.md.tmpl — fixed in 469d490 (profile reference, seat binding, drain-restart same-seat switch route).
- AGENTS.md — no impact: commands, constraints, validation policy unchanged.
- skills/, hosts/grok-bot/ — generated; render-skills.py --write no change, --check PASS.
- Historical CHANGELOG sections and dated design docs — no change.

Result: DOCKED
