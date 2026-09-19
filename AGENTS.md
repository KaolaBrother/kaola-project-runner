# Project Instructions

<!-- KW-AGENTS-MANAGED-START -->
global_contract_schema: 1

This managed region contains project facts only. The compatible machine-global workflow contract
owns universal engineering and lifecycle behavior. Owner content outside this region is preserved.

## Project Snapshot

- Purpose: runtime-neutral Agent Skills CLI communication driver for nine AI CLI platforms via tmux, plus the generated main orchestrator Skill `kaola-project-runner` (display name Project Runner; Codex, generic, and ZCode entries) and the generated external Skill `kaola-delegator` (display name Kaola-Delegator; Grok Bot, generic, and Codex entries). Codex remains a supported consuming runtime. Grok Bot is a bridge host that receives exactly one thin generated account Skill (`hosts/grok-bot/kaola-delegator.md`) which binds an execution target, asks that target's device-local locator (`scripts/kaola-locate.py`, link `kaola-project-runner-locate`) for the verified checkout, and loads `kaola-delegator`; that Skill starts one ZCode Host which then loads Project Runner; progressive disclosure is a locked invariant with byte budgets in `templates/budgets.json`; Grok Bot is not a ninth worker, not a Project Runner host, and has no installer destination.
- Stack: Bash (macOS-compatible), Python 3, tmux.
- Architecture: shared worker template renders nine self-contained platform Skills from YAML manifests and shell adapters; a separate orchestrator template renders the control-plane Skill (not a tenth platform); `templates/kaola-delegator/` renders the external Kaola-Delegator Skill; relay manages nested PTY.

## Commands

- Install: `./scripts/render-skills.py --write && ./scripts/install-local.sh [--runtime NAME | --skills-dir ABS_PATH] [--method link|copy] [--platform ID[,ID...]] [--no-orchestrator]`
- Test: `./scripts/validate.sh`
- Lint/typecheck/build: `./scripts/render-skills.py --check`
- **Release: before tagging/publishing any new version, verify every platform's pin/adapter requirements are met — e.g. the Grok Bot bridge must have a `saveable: true` pin (pin commit P naming content commit R at the release tag) — or explicitly record why a platform is intentionally not pinned this release.**
- Dev server: N/A

## Project Constraints

- Security boundary: prompts via relay literal/bracketed-paste, never shell eval; terminal controls rejected before PTY write.
- Public contract or compatibility constraints: `templates/grok-golden/` is frozen; worker Skills are generated from `templates/SKILL.md.tmpl`; the main orchestrator Skill is generated from `templates/orchestrator/`; the external Kaola-Delegator Skill is generated from `templates/kaola-delegator/`.
- Files or generated surfaces requiring special handling: `skills/` and `hosts/grok-bot/` are generated output, never hand-edit.

## Validation Policy

- Focused validation: `./scripts/render-skills.py --check` and `./scripts/validate.sh`
- Required integration validation: live tmux smoke per platform (start/observe/send/capture/stop)
- Environment or service acceptance: requires tmux, python3, and the target CLI binary

## Documentation Map

- `README.md` — four-tier entry (Kaola-Delegator / Project Runner / Platform Runner / Workflow Next), overview, and usage.
- `CHANGELOG.md` — user-visible changes when present.
- `docs/` — architecture, APIs, conventions, and decisions when present.

## Local Overrides

- Project-only precedence or exception: `none`
- Local development gotcha: `unknown`
<!-- KW-AGENTS-MANAGED-END -->

## Layered entry

Pick the most direct entry for the control you want. Do not force every task through every
layer. Each layer finishes its own job and does not repeat the next. Detail: `README.md`.

- **Kaola-Delegator** (`kaola-delegator`): external delegation (Grok Bot / generic / Codex).
  Hand off goal, progress, authorized platforms/quota/priority, and stop boundary to **one**
  ZCode ACP Host that must load Project Runner. The outer Agent does not bind workers or run
  the inner heartbeat. Included in v0.4.0; installation on a consuming machine and Grok Bot
  account-side live UAT require separate verification.
- **Project Runner** (`kaola-project-runner`): project control plane (Codex / generic / ZCode).
  Recover authorization, plan, dispatch, heartbeat, accept before finalize, close-out. **One
  project has only one Agent running this Skill.**
- **Platform Runner**: exact-session transport and lifecycle facts for one or a few issues. No
  task planning or completion judgment.
- **Workflow Next**: this Agent claims or resumes and advances one issue. Finalize/archive/sink
  belong to Workflow finalize. One issue is one run; several issues are not a bundle.

Start and stop use the bound canonical project root and an exact session. Do not add a
multi-Host registry, lock, second scheduler, or Delegator pointer file. Control-plane limits
do not change standalone Platform Runner transport. When the outer Agent changes, recover the
same live Host from the canonical Git root, the standard Runner session name, and existing
Runner `status` / receipts: `--session`, `acp_session_id`, and native `sess_*` as three
separate facts. A Git worktree is not an ACP id. A live Host is attached in place. If it is
confirmed stopped and `sess_*` cannot restore, a new standard-named Host is a new ACP
session: confirm current authorization before `start`, then continue from existing
project records. Do not open a blank Host. Grok Bot via the account bridge
attests Host status/start/resume/send/stop with the existing locator
`--project --worker zcode --session` (exact live name) and refuses `refused`;
Codex and generic do not.

## Project-Specific Runner Contract

- Project Runner Skills only identify, start, capture, send, read, and stop an exact owned tmux CLI
  session. The controlling Agent owns prompts, native keys, semantic judgments, orchestration, and
  recovery; there is no default Workflow command, heartbeat, cadence, lifecycle, or completion policy.
- The generated Skill `kaola-project-runner` (display name Project Runner) is the main control-plane
  Skill: it owns intake recovery, heartbeat, dispatch, acceptance-before-finalize, and close-out
  ownership. The nine platform Skills remain transport-only.
- Report complete terminal, process, relay, repository, Workflow, and forge facts. Activity, editor,
  approval, decision, model, Git, Workflow, and snapshot observations never authorize or block an
  Agent-selected transport; ordinary live change is evidence, not staleness.
- Refuse only objective transport impossibility or ambiguous/foreign target identity. A new classifier
  that blocks previously working automation is regression evidence; remove the restriction instead of
  adding another gate.
- Treat an unusually long Runner procedure or validation loop as overengineering evidence. Stop and
  reduce it to direct start, send, read, connection, and exact-stop proof instead of adding harnesses,
  classifiers, retries, or waiting layers.
- Keep `templates/grok-golden/` frozen. Change worker Skills through shared templates, platform facts,
  and adapters, the main Skill through `templates/orchestrator/`, and Kaola-Delegator through
  `templates/kaola-delegator/`, then run `./scripts/render-skills.py --write` and `--check`.
- Validate with `./scripts/validate.sh` and record exact outcomes. Live Cursor experiments use
  `cursor-grok-4.6-xhigh` with Fast disabled and never use `/model` as a read-only probe. A model
  mismatch remains evidence and must not disable communication.
- Ordinary Workflow-backed work starts the worker session at the consuming project's canonical
  project root and asks that runtime to invoke workflow-next in-session; the worker's Workflow
  owns the child worktree. Linked-worktree starts and existing-run recovery remain Agent
  decisions for standalone Platform Runner use and legacy in-flight sessions, not transport
  gates. Project Runner orchestrator mode (Issue #73) binds new dispatch to that canonical
  root without rewriting or globally forbidding those exceptions.
