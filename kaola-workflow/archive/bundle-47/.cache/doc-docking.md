# Documentation docking — Issue #47

DOCKED. Candidate `0264b534f245dd8a8210d03245e92dfed97dcb8c`.

Checked against generated `skills/kaola-project-runner/SKILL.md` `## Delivery` and the heartbeat skeleton: prefer the selected authorized Workflow sync/merge when a PR is not required; a PR is not opened merely for handoff when that sink is suitable; actionable open PRs take contested suitable capacity; other authorized work continues in parallel across permitted CLIs; a blocked PR keeps owner and next action without a global hold.

## Checked files

- `README.md` — UPDATED: main orchestrator paragraph states Workflow merge preference, no PR merely for handoff, and conditional open-PR priority with permitted-CLI parallel work.
- `docs/architecture.md` — UPDATED: control-plane sentence names selected Workflow sync/merge when a PR is not required and contested-capacity open-PR progress in parallel.
- `docs/conventions.md` — UPDATED: project-level contract names Workflow merge preference with conditional open-PR priority on the generated main Skill.
- `CHANGELOG.md` — UPDATED: Unreleased entry for issue #47 matches the Skill rule.
- `docs/api.md` — NO-IMPACT: renderer/installer/transport contract unchanged; this issue is orchestrator delivery-path guidance.
- `AGENTS.md` — NO-IMPACT: managed snapshot still names `templates/orchestrator/` as the main Skill source and workers as transport-only; the delivery-path rule lives in that Skill, not a new public command or API.
- `templates/grok-golden/` and worker Skills — NO-IMPACT: `git diff ed508b5 -- templates/grok-golden templates/SKILL.md.tmpl skills/claude-code-kaola-project-runner skills/codex-kaola-project-runner skills/cursor-cli-kaola-project-runner skills/devin-kaola-project-runner skills/grok-kaola-project-runner skills/kimi-cli-kaola-project-runner skills/opencode-kaola-project-runner` empty.

Live seven-platform tmux smoke and host wake-up were not re-run: Issue #47 marks Runner transport and host wake-up out of scope.
