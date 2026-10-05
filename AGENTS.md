# Project Instructions

<!-- KW-AGENTS-MANAGED-START -->
global_contract_schema: 1

This managed region contains project facts only. The compatible machine-global workflow contract
owns universal engineering and lifecycle behavior. Owner content outside this region is preserved.

## Project Snapshot

- Purpose: runtime-neutral Agent Skills CLI communication driver for ten AI CLI platforms via ACP, plus the generated main orchestrator Skill `kaola-project-runner` (display name Project Runner; Codex, generic, and ZCode entries) and the generated external Skill `kaola-delegator` (display name Kaola-Delegator; Grok Bot, generic, and Codex entries). Codex remains a supported consuming runtime. Grok Bot is a bridge host that receives exactly one thin generated account Skill (`hosts/grok-bot/kaola-delegator.md`) which binds an execution target, asks that target's device-local locator (`scripts/kaola-locate.py`, link `kaola-project-runner-locate`) for the verified checkout, and loads `kaola-delegator`; that Skill starts one CLI Host of any supported platform which then loads Project Runner; progressive disclosure is a locked invariant with byte budgets in `templates/budgets.json`; Grok Bot is not a worker platform, not a Project Runner host, and has no installer destination.
- Stack: Bash (macOS-compatible), Python 3.
- Architecture: shared worker template renders ten self-contained platform Skills from YAML manifests and shell adapters; a separate orchestrator template renders the control-plane Skill (not an eleventh platform); `templates/kaola-delegator/` renders the external Kaola-Delegator Skill; every worker communicates over ACP only through one ACP holder per session (PTY retired, #130).

## Commands

- Install: `./scripts/render-skills.py --write && ./scripts/install-local.sh [--runtime NAME | --skills-dir ABS_PATH] [--method link|copy] [--platform ID[,ID...]] [--no-orchestrator]`
- Test: `./scripts/validate.sh`
- Lint/typecheck/build: `./scripts/render-skills.py --check`
- **Release: before tagging/publishing any new version, verify every platform's pin/adapter requirements are met — e.g. the Grok Bot bridge must have a `saveable: true` pin (pin commit P naming content commit R at the release tag) — or explicitly record why a platform is intentionally not pinned this release. Every CHANGELOG release section states whether running seats must restart (`Seats: restart required` or `Seats: restart not required`). The operator test is `git diff OLD NEW -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms` (holder, bridge, holder-pinned quota catalog, or protocol). See `docs/conventions.md`.**
- Dev server: N/A

## Project Constraints

- Security boundary: prompts travel over ACP stdio JSON-RPC, never shell eval; outbound text is redacted (#51).
- Public contract or compatibility constraints: `templates/grok-golden/` is frozen; worker Skills are generated from `templates/SKILL.md.tmpl`; the main orchestrator Skill is generated from `templates/orchestrator/`; the external Kaola-Delegator Skill is generated from `templates/kaola-delegator/`.
- Files or generated surfaces requiring special handling: `skills/` and `hosts/grok-bot/` are generated output, never hand-edit.

## Validation Policy

- Focused validation: `./scripts/render-skills.py --check` and `./scripts/validate.sh`
- Required integration validation: live ACP smoke per platform (start/observe/send/capture/stop)
- Environment or service acceptance: requires python3 and the target CLI binary
- Full-contract dev machine: `tmux`, bash >= 4 (`mapfile`/`BASHPID`), and Python >= 3.10; a missing prerequisite skips its affected rows with a named receipt (#151)

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
  CLI ACP Host (any supported platform, #187) that must load Project Runner. The outer Agent
  does not bind workers or run the inner heartbeat. Included in v0.4.0; installation on a consuming machine and Grok Bot
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
Runner `status` / receipts: `--session`, `acp_session_id`, and the platform's native resume
id (ZCode `sess_*`) as three separate facts. A Git worktree is not an ACP id. A live Host is
attached in place. If it is confirmed stopped and that native id cannot restore, a new standard-named Host is a new ACP
session: confirm current authorization before `start`, then continue from existing
project records. Do not open a blank Host. Grok Bot via the account bridge
attests Host status/start/resume/send/stop with the existing locator
`--project --worker <Host platform> --session` (exact live name) and refuses `refused`;
Codex and generic do not.

## Project-Specific Runner Contract

- Project Runner Skills only identify, start, capture, send, read, and stop an exact owned ACP CLI
  session. The controlling Agent owns prompts, native keys, semantic judgments, orchestration, and
  recovery; there is no default Workflow command, heartbeat, cadence, lifecycle, or completion policy.
- Scoped exception (#255, Host carrier and Sideagent nodes only): when a Project Runner Host binds
  its Sideagent with `"mode": "node"`, that Host's holder starts one fresh node per batch of Host
  business changes from an ended Host turn (worker events still go to the Host), from the recorded
  Runner argument list (never a shell), sends it one batch prompt, reads its state checkpoint,
  wakes the Host once when that changed the Host's attention, and exact-stops it by holder. An explicit `--preserve-dispatched-workers` Host stop keeps
  that Host's proven worker trees. Standalone Platform Runner transport, default stop and every
  session not bound this way are unchanged.
- The generated Skill `kaola-project-runner` (display name Project Runner) is the main control-plane
  Skill: it owns intake recovery, heartbeat, dispatch, acceptance-before-finalize, and close-out
  ownership. The ten platform Skills remain transport-only.
- Report complete terminal, process, holder, repository, Workflow, and forge facts. Activity, editor,
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
  `grok-4.7-xhigh` with Fast disabled and never use `/model` as a read-only probe. A model
  mismatch remains evidence and must not disable communication.
- Ordinary Workflow-backed work starts the worker session at the consuming project's canonical
  project root and asks that runtime to invoke workflow-next in-session; the worker's Workflow
  owns the child worktree. Linked-worktree starts and existing-run recovery remain Agent
  decisions for standalone Platform Runner use and legacy in-flight sessions, not transport
  gates. Project Runner orchestrator mode (Issue #73) binds new dispatch to that canonical
  root without rewriting or globally forbidding those exceptions.

## User special requirements — lifecycle implementation (#255)

Source: explicit owner request, 2026-10-04. Scope: the current lifecycle/state-maintenance implementation and its final acceptance. These seven items clarify the agreed goals; they do not authorize a second framework or unrelated work. Only owner requests or owner-confirmed proposals belong in this section; reconcile superseded requirements when the owner changes them.

1. **Template fidelity.** Demonstrate how both Delegator and Host heartbeat entries match their applicable canonical templates, how drift is detected and corrected, and what happens when native timer readback is unavailable. Keep changing project state out of timer text.
2. **Structured, current and inspectable information.** Demonstrate across repeated cycles that heartbeat inputs and durable evidence do not become dominated by obsolete, duplicate or conflicting information. Update current records, reconcile contradictions from sources, retire resolved responsibilities and reference history without losing pending duties, authorization or unresolved evidence. Legitimate current work may grow. Judge efficiency by correct completion, elapsed time, rework, user intervention and resources, not prompt length or total tokens alone. Owner clarification, 2026-10-05 (#259): demonstrate the agreed information/state-maintenance contract end to end. The two routine JSONs have fixed typed fields, explicit role ownership and tool-enforced writes and consumer views; they retain current authorization, work, decisions and recovery duties, not agent-created historical snapshots or parallel memory. Native heartbeat text remains the canonical entry only. Owner-confirmed special requirements live in AGENTS.md and are visible to the user; meaningful project evidence and prior versions are traced through existing Git commits/history and original evidence references. Ordinary task notes elsewhere remain allowed. Tools and Sideagent maintain process facts within their responsibilities; Delegator and Host retain their own decisions. Existing supervision must detect stale, conflicting, missing or out-of-contract information and support correction, with human-readable current views and evidence links. Verify this through repeated operation, context recovery and upgrade, preserving pending instructions, grants and in-flight work; a prompt reminder or a one-time valid JSON is not acceptance. Owner acceptance criterion: coordination must not turn Delegator or Host work into repeated bookkeeping, receipt narration, state audits or record repair that displaces project progress. Use the observed VRPAI/VRPCAD runs as regression cases: show useful task advancement alongside maintained state, with routine facts updated as part of existing operations and process reconciliation delegated to Sideagent. Correct JSON alone cannot establish success.
3. **Host autonomy and Sideagent lifecycle.** Trace role entry, tool discovery, actual calls and recovery. Host directly reads/searches/analyzes or performs simple authorized work; it selects workers, authors assignments, invokes dispatch tools and judges original results. Tools maintain deterministic facts; fresh Sideagent nodes reconcile meaningful batches of duties, conflicts and exceptions, without routine per-event startup. Preserve required lifecycle touchpoints and exact identities; no compulsory Sideagent round trip or new tool-permissions framework. Split parallel work at independent context/resource boundaries; no fixed reviewer count or unrelated all-branch barrier.
4. **Cadence-independent supervision.** Demonstrate supported 30-minute, 1-hour, 2-hour and 4-hour inquiry configurations using the existing timer. At each applicable inquiry, supervise and advance tasks, relay owner instructions/feedback, reconcile current shared state and report unresolved decisions. Verify adoption rather than treating delivery as completion. These examples do not change this run's authorized hourly cadence or create extra timers.
5. **Recovery and informed autonomy.** Cover material edge cases, blocking conditions and failures with tested recovery paths or actionable evidence, responsible roles and next steps. Use representative real-run cases and a small set of different combinations not used to tune the change; distinguish environment/configuration failures from model behavior and assess actual outcomes, not merely valid JSON. Reuse existing QA without a second evaluation framework. Preserve safe agent discretion and direct degraded/emergency paths; report verified coverage, limitations and unknowns, never universal fault freedom.
6. **Learning from mistakes.** Assess whether repeated operation lets agents use preserved failure/outcome evidence to correct decisions and avoid repeating errors, and demonstrate that correction where feasible. Distinguish state correction and task-plan adaptation from changes to product rules/tools: retain existing authorization, user decisions and normal reviewed changes. Retire obsolete or duplicative guidance when evidence supports doing so; do not add a universal rule for every incident. Do not infer permission for a new self-modification engine or unbounded history store.
7. **Future upgrade continuity.** Establish a repeatable update convention and tested migration path from supported previous versions, preserving effective grants, duties, in-flight work and unresolved exceptions. Cover interrupted/repeated migration, compatible readers/holders and actionable recovery. Use installed runtime versions, matching adapters and actual applied configuration/receipts as evidence; API documentation alone does not establish CLI/ACP support. State unsupported or unverified paths honestly.

Completion report: answer all seven items against the final integrated candidate, with mechanism, actual evidence/result, and remaining limitations. The outer Delegator personally reviews this with Claude Code Opus Extra High. Exercise this very requirement's record → relay → adoption → implementation/QA → final answer path using existing records and receipts, so progress remains aligned with the agreed goals. Reuse meaningful evidence; do not add a parallel ledger, scheduler or duplicate acceptance phase.
