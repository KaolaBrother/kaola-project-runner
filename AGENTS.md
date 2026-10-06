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

- Focused validation: `./scripts/render-skills.py --check` and the affected contract suites through `./scripts/validate.sh --suite <inventory-basename>` (repeatable; an explicit subset, not an inferred dependency graph; unknown names are refused)
- Whole-inventory validation: `./scripts/validate.sh` (no `--suite`) when actual changes, remaining gaps or a binding requirement justify it; never mandatory merely for a return, commit, integration/release or QA label
- Required integration validation: live ACP smoke per platform (start/observe/send/capture/stop)
- Environment or service acceptance: requires python3 and the target CLI binary
- Full-contract dev machine: `tmux`, bash >= 4 (`mapfile`/`BASHPID`), and Python >= 3.10; a missing prerequisite skips its affected rows with a named receipt (#151)
- Evidence reuse: an unchanged valid result stays valid; a new commit does not invalidate all prior results. A build cache is not a result cache. A toolchain, configuration, fixture, feature, platform or external input change can invalidate evidence.
- Slow feedback: give a concrete smaller scope, a reused valid result, or a bounded fixture/module split or decoupling. If a check cannot shrink, name its unique coverage and move it to the allowed integration or release boundary. Do not only raise a timeout or run more copies of the full gate; the hang watchdog is not a normal feedback budget, and there is no universal elapsed-time gate or new monitor.

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
  business changes or verified session-bound completed HOST compaction recovery inputs
  at an ended Host turn (worker events still go to the Host), from the recorded
  Runner argument list (never a shell), sends it one batch prompt, reads its state checkpoint,
  wakes the Host once when that changed the Host's attention, and exact-stops it by holder. An explicit `--preserve-dispatched-workers` Host stop keeps
  that Host's proven worker trees. The carrier registers mechanical recovery inputs
  and failures through the locked state tool, without Host business writes; the node
  checks original scoped sources and its checkpoint names the actual sent input,
  batch and node holder. Native Skill reload remains a separate duty. Standalone Platform Runner transport, default stop and every
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
- Validate the affected suites through `./scripts/validate.sh --suite <inventory-basename>` for development feedback; run the whole inventory only when actual changes, remaining gaps or a binding requirement justify it; record exact outcomes. Live Cursor experiments use
  `grok-4.7-xhigh` with Fast disabled and never use `/model` as a read-only probe. A model
  mismatch remains evidence and must not disable communication.
- Ordinary Workflow-backed work starts the worker session at the consuming project's canonical
  project root and asks that runtime to invoke workflow-next in-session; the worker's Workflow
  owns the child worktree. Linked-worktree starts and existing-run recovery remain Agent
  decisions for standalone Platform Runner use and legacy in-flight sessions, not transport
  gates. Project Runner orchestrator mode (Issue #73) binds new dispatch to that canonical
  root without rewriting or globally forbidding those exceptions.

## Project special requirements — lifecycle implementation (#255)

Source: explicit owner request, 2026-10-04. Scope: the current lifecycle/state-maintenance implementation and its final acceptance. Host and Delegator apply these project requirements within their existing responsibilities. These six items clarify the agreed goals; they do not authorize a second framework or unrelated work. Only owner requests or owner-confirmed proposals belong in this section; reconcile superseded requirements when the owner changes them.

1. **Template fidelity.** Demonstrate how both Delegator and Host heartbeat entries match their applicable canonical templates, how drift is detected and corrected, and what happens when native timer readback is unavailable. Keep changing project state out of timer text.
2. **Structured, current and inspectable information.** Demonstrate across repeated cycles that heartbeat inputs and durable evidence do not become dominated by obsolete, duplicate or conflicting information. Update current records, reconcile contradictions from sources, retire resolved responsibilities and reference history without losing pending duties, authorization or unresolved evidence. Legitimate current work may grow. Judge efficiency by correct completion, elapsed time, rework, user intervention and resources, not prompt length or total tokens alone. Owner clarification, 2026-10-05 (#259): demonstrate the agreed information/state-maintenance contract end to end. The two routine JSONs have fixed typed fields, explicit role ownership and tool-enforced writes and consumer views; they retain current authorization, work, decisions and recovery duties, not agent-created historical snapshots or parallel memory. Native heartbeat text remains the canonical entry only. Owner-confirmed special requirements live in AGENTS.md and are visible to the user; meaningful project evidence and prior versions are traced through existing Git commits/history and original evidence references. Ordinary task notes elsewhere remain allowed. Tools and Sideagent maintain process facts within their responsibilities; Delegator and Host retain their own decisions. Existing supervision must detect stale, conflicting, missing or out-of-contract information and support correction, with human-readable current views and evidence links. Verify this through repeated operation, context recovery and upgrade, preserving pending instructions, grants and in-flight work; a prompt reminder or a one-time valid JSON is not acceptance. Owner acceptance criterion: coordination must not turn Delegator or Host work into repeated bookkeeping, receipt narration, state audits or record repair that displaces project progress. Use the observed VRPAI/VRPCAD runs as regression cases: show useful task advancement alongside maintained state, with routine facts updated as part of existing operations and process reconciliation delegated to Sideagent. Correct JSON alone cannot establish success. Owner clarification, 2026-10-06 (#259): applicable unresolved exceptions alone belong in current collections. The existing clear/resolve/retire operation removes a handled row from stored state atomically; all role views and injected bodies derive from that collection. Keep no resolved row, tombstone or retrospective text in another routine field. Revoked/expired eligibility leaves its applicable collection; unfinished stop/handoff/reclaim effects remain only concrete current duties. Tools validate positive types and transitions; Agents judge semantic currentness. Refusals name an existing collection/id, current revision and executable removal operation with original evidence requirements. For an absent row, do not create it. A genuinely unresolved unclassified matter retains original evidence on the existing current decision/reconciliation route until its proper type is established. Unknown is not resolved. Preserve newer maintenance, effective grants, instructions and live links. Owner clarification, 2026-10-06 (#259): the Delegator user-facing heartbeat report includes a concise derived current Elite/Expert summary: exact preset ids, counts, Expert lifetime, occupied linked tasks and available/held/unknown capacity. Count shared tiers once, derive totals from effective grant/shared counts and occupancy; keep service/quota/fault restrictions in their proper roles, and exempt Host/Sideagent/Pool roles. Missing Expert authorization is none. Use current authorization, dispatch/task links and verified Runner facts; store no second seat table or occupancy rows. Host uses the existing dispatch projection on demand, with no compulsory heartbeat section or injection. Native timer entry stays canonical. Owner clarification, 2026-10-06 (#259/951): authorization records exact preset/shared grant counts and lifetime/switch restrictions, with no separately writable elite_cap, total_cap, worker_pool_cap or renamed aggregate limit. Totals/availability derive from current grants and verified occupancy. Remove redundant legacy limits through migration; conflicting or total-only intent requires specific source-based owner recovery, not silent authority expansion. The owner revoked this run cap4; possible Elite capacity derives from current individual/shared grants, including later explicit owner count corrections, with Host/Sideagent separate and Worker pool unchanged. Owner clarification, 2026-10-06 (#259/955): keep one canonical grant/group count, choices and switch permission; choices alone do not authorize switching. Derive capabilities, Class/profile/default model/effort from version-matched catalog, grants, default Worker pool, exclusions, holds and availability; retain only explicit owner overrides. Generate compatibility rows from grouped grants. Remove settled authorization and relays, preserving active Worker exclusions, paused grants with reopening duties and unresolved exact stop/handoff. Keep one pause authority, a concise objective and original source pointers. Project owner requirements remain in this AGENTS user section; routine JSON does not copy requirements, Skill rules, adoption history or a second freeform requirements store. Ambiguous legacy authority requires source-based owner recovery; no silent expansion.
3. **Host autonomy and Sideagent lifecycle.** Trace role entry, tool discovery, actual calls and recovery. Host directly reads/searches/analyzes or performs simple authorized work; it selects workers, authors assignments, invokes dispatch tools and judges original results. Tools maintain deterministic facts; fresh Sideagent nodes reconcile meaningful batches of duties, conflicts and exceptions, without routine per-event startup. Preserve required lifecycle touchpoints and exact identities; no compulsory Sideagent round trip or new tool-permissions framework. Split parallel work at independent context/resource boundaries; no fixed reviewer count or unrelated all-branch barrier.

   Owner clarification, 2026-10-06 (#259/#264): a verified, session-bound HOST compaction-completed signal must create one bounded Sideagent recovery reconciliation independently of a Host business-state write or a remembered request. Preserve the current installed Skill reload; native-owned reload does not suppress the separate maintenance duty. At the existing safe boundary, coalesce compatible pending maintenance and repeated notifications for the same occurrence without interrupting the Host or starting a node for worker compaction. Keep a real pending duty until a valid scoped checkpoint or a visible failure with a recovery obligation. Sideagent checks current owner goal/authorization, pending duties/decisions and task-dispatch-result/reclaim links against original evidence; it cannot reconstruct unrecorded thoughts, invent tasks, accept results or rewrite Host judgments. Where no verified completed signal exists, retain the existing Delegator inquiry fallback and name that limitation. The inquiry can detect unresolved process duties, missing/failed maintenance binding or missing checkpoint and request bounded reconciliation without a new Host revision. No fake business edit, unconditional all-state audit, independent timer, blanket timeout, new scheduler or ledger. Review the minimal design and focused actual activation/recovery QA with the appointed dot main thread and authorized Claude Code Fable, both personally reviewing and passing, before declaring this covered; this direction is not an implemented result. This concrete direction supersedes the broader earlier relay195 inference.
4. **Recovery and informed autonomy.** Cover material edge cases, blocking conditions and failures with tested recovery paths or actionable evidence, responsible roles and next steps. Use representative real-run cases and a small set of different combinations not used to tune the change; distinguish environment/configuration failures from model behavior and assess actual outcomes, not merely valid JSON. Reuse existing QA without a second evaluation framework. Preserve safe agent discretion and direct degraded/emergency paths; report verified coverage, limitations and unknowns, never universal fault freedom. Owner clarification, 2026-10-05: for potentially transient network/service failures, require at least three safe retries after the initial failure before declaring persistent agent/runtime failure. Reconcile prior effects before retrying; never blindly replay an unknown mutation, and do not count an in-progress connection as a failed attempt. A recovered attempt clears the transient failure claim; repeated failures alone do not prove root cause. Explicit authentication, quota and rate-limit refusals retain the existing user/class-specific handling, with no login or credential retries. If safe retries are unavailable, report uncertainty and the recovery path instead of asserting a persistent fault.
5. **Continuous improvement and evolution.** Owner clarification, 2026-10-06: improve both the project and how work is done during ordinary execution; a mistake or failure is not a prerequisite. The Host must notice redundancy in tests, modules, functions, interfaces, configuration, documentation and coordination processes during normal planning, implementation review and QA, without waiting for a user reminder. Also use preserved failure/outcome evidence to correct decisions and avoid repeated errors. Assess structural duplication, excessive coupling, long waits, costly verification and poor responsibility allocation against the simplest-sufficient-design principle. Distinguish unnecessary duplication from deliberate isolation and distinct required behavior. Select bounded merge, reuse, simplification or removal while preserving correctness, compatibility and effective user constraints. Use suitable Worker-Class agents for independent public/source research when useful. The current concrete research case is long whole-gate testing in Rust, Swift and Kaola-Workflow: affected-module/dependency coverage, splitting and decoupling, valid evidence reuse, duration warnings with required corrective action, and parallel exploratory QA. Compare useful outcomes, correctness, elapsed time, rework, user intervention and resources before retaining improvements. Keep existing ownership, authorization and reviewed delivery; propose broader changes with concrete evidence and scope. Give the Host a clear executable improvement path using existing tools: locate redundant responsibilities and coupled dependencies, define the preserved outcome and affected boundary, compare a minimal simplification, resolve material scope/value choices with the user, improve independently testable parts, then verify their integrated interfaces, data flow and recovery. Tool outputs should expose relevant dependencies, change impact and existing verification entry points; the Host retains architectural and scheduling judgment. Local success does not prove integrated correctness. Prefer a coherent, reliable system with justified components over isolated perfection or an absolute zero-redundancy claim. Do not weaken meaningful checks or let speculative optimization replace delivery. Retire obsolete guidance instead of adding a rule for every incident. Use existing tasks/issues and Git/original evidence; retain only current improvement duties in routine state. No mandatory per-task optimization phase, separate recurring audit, redundancy ledger, self-modification engine or unbounded history store.
6. **Future upgrade continuity.** Establish a repeatable update convention and tested migration path from supported previous versions, preserving effective grants, duties, in-flight work and unresolved exceptions. Cover interrupted/repeated migration, compatible readers/holders and actionable recovery. Use installed runtime versions, matching adapters and actual applied configuration/receipts as evidence; API documentation alone does not establish CLI/ACP support. State unsupported or unverified paths honestly.

Completion report: answer all six items against the final integrated candidate, with mechanism, actual evidence/result, and remaining limitations. Exercise this requirement's record → relay → adoption → implementation/QA → final answer path using existing records and receipts, so progress remains aligned with the agreed goals. Reuse meaningful evidence; do not add a parallel ledger, scheduler or duplicate acceptance phase.

## Delegator special requirements — issue 259 final acceptance

Source: explicit owner appointment, clarified 2026-10-06 (#259). Scope: this run's outer supervision and user communication. Only owner requests or owner-confirmed proposals belong here; replace superseded requirements when the owner changes them.

Owner correction, 2026-10-06: for this run, the dot main thread and Claude Code Fable must each personally review and pass the final integrated result before PATCH publication. This replaces the prior dot plus Opus appointment; final affected acceptance remains pending until both actual verdicts pass. Prior valid reviews remain evidence for unchanged scope. KPR independently owns one shared concurrent seat across all installed Claude Code tiers, currently default/opus-xhigh/fable/sonnet and future installed tiers; switching is authorized within that same seat. KPR Droid default/opus/core also share one concurrent seat in total under the latest owner correction; there is no separate seat per tier. The prior new-Claude-start pause is revoked. Use a tier for an actual authorized task, without a start merely to verify the reported reinstall; no new paid service or configuration change is authorized. Effective grants remain in the existing authorization record, and Fable retains its catalog thinking/review scope. This appointment applies to this run and adds no second seat, approval loop or project requirement. Ordinary Delegators do not inherit this personal audit or Fable review.
