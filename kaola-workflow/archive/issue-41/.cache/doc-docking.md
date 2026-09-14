# Documentation Docking — issue-41 (issue #41)

verdict: DOCKED
candidate: workflow/issue-41 @ a19f528c33d19e024529474c3178ad9f47464c36

Installer `--help` transcribed from `./scripts/install-local.sh -h` at this SHA:
`--no-orchestrator` is a usage flag; `--platform` filters worker Skills only;
`kaola-project-runner` is not a platform ID; the main Skill installs for every
`--runtime` / `--skills-dir` destination unless skipped.

## Checked files

- `README.md` — UPDATED: worker vs main orchestrator Skill; install examples
  including `--no-orchestrator`; golden is worker-history, not the orchestrator
  contract.
- `docs/architecture.md` — UPDATED: control-plane Skill in the product boundary
  diagram; `templates/orchestrator/` as the main-Skill contract; installer
  `--no-orchestrator` rule.
- `docs/api.md` — UPDATED: renderer writes seven workers plus
  `skills/kaola-project-runner/`; installer flag list matches `--help`.
- `docs/conventions.md` — UPDATED: heartbeat/acceptance live in the generated
  main Skill; orchestrator templates called out as source of truth.
- `docs/README.md` — UPDATED: architecture index line names worker vs main Skill.
- `AGENTS.md` — UPDATED: managed snapshot/install/constraints distinguish worker
  generation from `templates/orchestrator/`; owner region names the control-plane
  Skill without moving heartbeat onto workers.
- `CHANGELOG.md` — UPDATED: Unreleased entry for issue #41.
- `templates/orchestrator/` — NEW: English `SKILL.md.tmpl`, Codex display
  metadata, Chinese heartbeat skeleton as a reference file.
- `templates/SKILL.md.tmpl` — UPDATED: optional two-sentence pointer to the main
  Skill name; transport contract otherwise unchanged.
- `skills/` — GENERATED via `render-skills.py --write`; `--check` PASS at this
  SHA; never hand-edited.
- `templates/grok-golden/` — NO-IMPACT: frozen; `git diff origin/main...HEAD -- templates/grok-golden` empty.

## No-impact reasons

- Historical live-smoke and ACP Watch docs keep their original wording as dated
  records; this issue does not change transport adapters or smoke.
- Live per-platform tmux smoke was not re-run; the candidate does not change
  adapters or transport smoke, and Issue #41 forbids adding a recurring
  heartbeat to transport smoke.
