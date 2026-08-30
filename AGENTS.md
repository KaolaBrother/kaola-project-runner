# Project Instructions

## Project Snapshot

- Purpose: see `README.md` or project metadata; record `unknown` until verified.
- Stack: detect from the repository; record `unknown` until verified.
- Architecture: keep two or three verified bullets here, or record `unknown`.

## Commands

- Install: `unknown`
- Test: `unknown`
- Lint/typecheck/build: `unknown`
- Dev server: `unknown`

## Non-Negotiable Rules

- Think before coding: state assumptions, surface ambiguity, and ask when unclear.
- Read before writing: inspect the target and its surrounding conventions immediately before editing.
- Keep changes simple and surgical; solve the requested problem without speculative abstractions.
- Define verifiable success criteria before starting and loop until they pass.
- Keep acceptance meaning independent from the production code it judges.
- Verify APIs, interfaces, and behavior against documentation, source, or a real run; do not fabricate.
- Reuse an existing equivalent before adding a new interface.
- Escalate irreversible changes and user-owned public-contract decisions to the user.

## First Principles

1. Correct first; never trade correctness for speed or cost.
2. Then save human time without weakening correctness.
3. Then use the cheapest sufficient mechanism.
4. Machines decide facts; humans decide values.
5. Own local completion evidence instead of outsourcing the verdict.

## Runner Authority Boundary

- Project Runner Skills are CLI communication drivers: start the exact tmux session, read/capture
  output, transfer Agent-selected prompts or native keys, read the reply, and stop only that session.
- They discover and transfer; they do not decide, orchestrate, or block. A bare invocation has no
  default Workflow command, task mode, heartbeat, cadence, lifecycle, or completion policy.
- Collect the complete runtime frame and deterministic terminal, process, relay, repository, Workflow,
  and forge facts, then give that evidence to the controlling agent.
- Transfer the prompt or command chosen by the controlling agent and read the actual response back.
- Native selection keys are also Agent-owned input. The Runner may transfer an explicitly named key
  and attest its bytes, but must not infer what a visible option means or choose it automatically.
- Do not turn activity, editor, approval, decision, worker-count, coordinate, prose, Git, Workflow, or
  snapshot-change observations into authorization gates for agent-directed actions.
- A snapshot or revision may correlate an action with earlier evidence, but ordinary live change must be
  reported rather than refused as stale.
- The controlling agent owns all semantic judgment and recovery choices. The Skill reports objective
  transport impossibility or failure exactly; it does not disguise it as a runtime-status verdict.
- Treat a previously working real automation that becomes blocked by a new classifier, snapshot rule,
  label interpretation, or inferred state as regression evidence. Measure actual input, output, and
  durable effects; do not add another hard gate in response.

## Validation Policy

- Treat background hooks as advisory and avoid repeating validation they already completed.
- Record the exact commands and outcomes that establish completion.
- Run the smallest focused proof first, then the project-required integration surface.
- Cursor CLI live experiments must explicitly open the native `/model` selector, select a non-FAST
  Cursor Grok 4.6 variant, capture the selected model without a `Fast` suffix, and only then send the
  verification prompt. This is an experiment requirement owned by the validating Agent, not a Runner gate.

## Kaola-Workflow

<!-- KW-AGENTS-MANAGED-START -->
Everything between these markers is owned by `workflow-init`; owner content outside them is preserved.

<!-- PIN: forge-is-the-backlog -->
- Start or resume workflow work through the router entrypoint installed by the active runtime.
- The forge is the backlog authority; freshly verify issue state before it shapes implementation.
- `kaola-workflow/.roadmap/_rules.md` is the one optional local file that survives for standing project rules.
- nothing else is generated or tracked under `kaola-workflow/.roadmap/`; there is no local mirror to refresh.
- Top-priority labels: declare in `kaola-workflow/config.json` (`priority_top_tier_labels`).
- A run records its claim in `kaola-workflow/{project}/workflow-state.md` and its missions in
  `kaola-workflow/{project}/mission-list.md`.
- Keep each mission as `item`, `status`, `dispatched`, and `result`.
- Each entry is a mission, not a specification.
- The frontier is the list minus done minus in-flight; re-evaluate dispatch or inline for every item.
- One item never establishes a run-wide posture, and one unavailable exact role does not prove all native child dispatch is unavailable.
- **Three write moments.** Create the mission, record `dispatched` **before the work goes out**, then record `result` when it closes.
- `dispatched` records what went out, to whom, and where the output was to land.
- Once closed, the completed item and its result are immutable.
- One dispatch has one result, including `FAIL` or `BLOCKED`.
- A failed command, intermediate finding, repair attempt, or review round does not by itself create a mission.
- Keep working within the current promised outcome while custody and causal boundary remain unchanged.
- Append a mission only for a new recoverable outcome that changes custody or for a newly discovered independent causal class.
- Finalization, Issue closure, archive, and sink are not Mission List items. The last run mission establishes readiness for finalization. The finalization summary, closure evidence, archive state, and sink receipt own the transaction's truth.
- `BLOCKED` means the current owner cannot safely continue.
- Custody (who decides meaning) is independent of carrier (inline vs a native child).
- Converge the observed failure frontier before freezing a candidate and reviewing it.
- Name roles by function and reasoning tier, never by a vendor model name; write `planner (heavy-reasoning tier)`.
- Prefer the installed named role and follow this runtime's workflow-next / finalize capability guide for
  lookup, dispatch carrier, default tier binding, and available native routes.
- A built-in or generic child may take an item only as its real mechanism when it can satisfy the task, custody,
  evidence, and stop boundaries; never present it as a missing named role. Inline only that item when no adequate route exists.
- After resume or compaction, read the workflow state and mission list before continuing.
- Finalize only after focused and integration evidence pass, documentation is docked, and every finding closes.
- Archive completed run state through the installed workflow lifecycle rather than deleting it by hand.
<!-- KW-AGENTS-MANAGED-END -->

## Documentation Map

- `README.md` — project overview and usage.
- `CHANGELOG.md` — user-visible changes when present.
- `docs/` — architecture, APIs, conventions, and decisions when present.

## Documentation Update Checklist

- Update `README.md` when installation, setup, or usage changes.
- Update `docs/architecture.md` or `docs/api.md` when runtime boundaries or interfaces change.
- Update `CHANGELOG.md` for user-visible behavior changes.
- Record an explicit no-impact reason when none of those documents needs a change.

## Maintenance

- Keep this universal contract concise; move long procedures and runtime-only detail elsewhere.
- Add rules only after repeated mistakes, review feedback, or stable project conventions.
- Runtime-native first-read files may bridge to this file and carry only genuine runtime overlays.
