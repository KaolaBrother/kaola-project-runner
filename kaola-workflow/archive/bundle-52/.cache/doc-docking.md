# Documentation docking — bundle-52

Status: DOCKED.

- README.md: checked in candidate `291feb71bc9c6da8b4779fb8945ebe0e2ac775f7`. Collaborative delivery now states canonical-project-root start, in-session `workflow-next`, concurrent sessions, Normal path and Evidence-backed exception examples, and advisory child-worktree migration.
- docs/architecture.md: checked. Canonical project root versus Workflow child worktree is defined; `KAOLA_PROJECT_RUNNER_REPO` is the Agent-selected Git top-level realpath, not a classifier.
- docs/conventions.md: checked. Source-of-truth and no-adapter-gate wording match the templates.
- docs/api.md: checked. `--repo` remains Git top-level; linked worktree is valid on PTY and ACP and is not a transport refusal; `workflow-next` is an Agent-selected prompt.
- docs/README.md: checked. Architecture index mentions the new distinction.
- AGENTS.md: checked. Project-specific Runner contract restates the same default.
- CHANGELOG.md: checked. Unreleased entry matches shipped guidance. No version bump, tag, or published release in this run.
- Generated `skills/*/SKILL.md`, worker `references/transport.md`, and `skills/kaola-project-runner/references/workflow-worktree.md`: rendered from templates; `./scripts/render-skills.py --check` PASS. No hand edits.
- `hosts/grok-bot/`, `templates/grok-bot/`, `docs/grok-bot-host.md`, `templates/grok-golden/`: out of scope for #52; products unchanged.
