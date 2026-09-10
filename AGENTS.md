# Project Instructions

<!-- KW-AGENTS-MANAGED-START -->
global_contract_schema: 1

This managed region contains project facts only. The compatible machine-global workflow contract
owns universal engineering and lifecycle behavior. Owner content outside this region is preserved.

## Project Snapshot

- Purpose: Codex-facing CLI communication driver for six AI CLI platforms via tmux.
- Stack: Bash (macOS-compatible), Python 3, tmux.
- Architecture: shared template renders six self-contained Skills; each platform has a YAML manifest and shell adapter; relay manages nested PTY.

## Commands

- Install: `./scripts/render-skills.py --write && ./scripts/install-local.sh`
- Test: `./scripts/validate.sh`
- Lint/typecheck/build: `./scripts/render-skills.py --check`
- Dev server: N/A

## Project Constraints

- Security boundary: prompts via relay literal/bracketed-paste, never shell eval; terminal controls rejected before PTY write.
- Public contract or compatibility constraints: `templates/grok-golden/` is frozen; active Skills generated from `templates/SKILL.md.tmpl`.
- Files or generated surfaces requiring special handling: `skills/` is generated output, never hand-edit.

## Validation Policy

- Focused validation: `./scripts/render-skills.py --check` and `./scripts/validate.sh`
- Required integration validation: live tmux smoke per platform (start/observe/send/capture/stop)
- Environment or service acceptance: requires tmux, python3, and the target CLI binary

## Documentation Map

- `README.md` — project overview and usage.
- `CHANGELOG.md` — user-visible changes when present.
- `docs/` — architecture, APIs, conventions, and decisions when present.

## Local Overrides

- Project-only precedence or exception: `none`
- Local development gotcha: `unknown`
<!-- KW-AGENTS-MANAGED-END -->

## Project-Specific Runner Contract

- Project Runner Skills only identify, start, capture, send, read, and stop an exact owned tmux CLI
  session. The controlling Agent owns prompts, native keys, semantic judgments, orchestration, and
  recovery; there is no default Workflow command, heartbeat, cadence, lifecycle, or completion policy.
- Report complete terminal, process, relay, repository, Workflow, and forge facts. Activity, editor,
  approval, decision, model, Git, Workflow, and snapshot observations never authorize or block an
  Agent-selected transport; ordinary live change is evidence, not staleness.
- Refuse only objective transport impossibility or ambiguous/foreign target identity. A new classifier
  that blocks previously working automation is regression evidence; remove the restriction instead of
  adding another gate.
- Treat an unusually long Runner procedure or validation loop as overengineering evidence. Stop and
  reduce it to direct start, send, read, connection, and exact-stop proof instead of adding harnesses,
  classifiers, retries, or waiting layers.
- Keep `templates/grok-golden/` frozen. Change active Skills through shared templates, platform facts,
  and adapters, then run `./scripts/render-skills.py --write` and `--check`.
- Validate with `./scripts/validate.sh` and record exact outcomes. Live Cursor experiments use
  `cursor-grok-4.6-xhigh` with Fast disabled and never use `/model` as a read-only probe. A model
  mismatch remains evidence and must not disable communication.
