---
name: kimi-cli-kaola-project-runner
description: Use when Codex should run Kaola Workflow through a Kimi CLI main conversation in an exact tmux session. A bare invocation uses the current Git repository and starts workflow-next so it can select the most appropriate Issue batch; extra prompt text can refine the goal or mode, while recurring Kimi CLI execution remains explicit.
---

# Kimi CLI Kaola Project Runner

This is a Codex-only skill. Run one project through one exact tmux session and one Kimi CLI main
conversation. Kimi CLI owns the project run; Kaola Workflow owns its durable lifecycle. A loop is never
the default.

## Bare invocation starts immediately

`$kimi-cli-kaola-project-runner` by itself is a complete request. Do not ask the user to add parameters,
choose a mode, or restate a goal.

1. Resolve the canonical Git top-level containing the current working directory and use it as the
   workspace repository. Do not search siblings or use a remembered repository.
2. Select **Complete one Workflow project**.
3. Derive the exact tmux session as `kimi-cli-kaola-<repo-basename>`, replacing characters outside
   letters, digits, dot, underscore, and hyphen with `-`.
4. Run preflight, start or reuse the exact owned Kimi CLI main conversation, and send the one-shot
   prompt from [references/project-run.md](references/project-run.md) as soon as that main
   conversation is ready for input.
5. Tell Kimi CLI to invoke `workflow-next` immediately without an individual Issue target. Let the
   current `workflow-next` contract inspect repository and forge state, then select the most
   appropriate coherent Issue batch for efficient execution. Do not preselect one Issue, set a
   single-Issue target, or turn the current directory into an Issue hint.
6. Create the 15-minute Codex supervision heartbeat after the run starts. Do not create a Kimi CLI
   scheduler unless recurring work was explicitly requested.

Extra prompt text is optional and only refines these defaults. An explicit repository, mode,
session, goal, PR, or interval overrides the corresponding default. In project mode, a mentioned
Issue supplies goal context; it does not narrow `workflow-next` to a one-Issue run or prevent it
from selecting the related batch. Stop for input only when the current directory is not inside a
Git repository, preflight cannot establish safe ownership, or a material user decision is
genuinely required.

## Full lifecycle

`create/start → Codex 15m supervision → resume → observe/report → optional Kimi CLI recurring work → decision → finalize/close → stop`

Codex performs all control through CLI evidence: inspect Git and Kaola state in the repository,
operate the Kimi CLI TUI through tmux, and verify forge state with the available CLI. No desktop UI is
required. The skill exposes task modes to Codex, not business subcommands. Codex decides and sends
the Kimi CLI prompts described here; `scripts/runtime-tmux.sh` is only a safe low-level control helper.

> Adapter capability gate: recurring execution is currently `unsupported` for Kimi CLI. Modes 2 and 4 below preserve the Grok golden-contract parity target but are unavailable; do not emulate them with a heartbeat, background agent, goal, loop, task, or detached conversation.

## Four exposed capabilities

Read [references/task-modes.md](references/task-modes.md), select the explicit mode or mode 1 by
default, and preserve its scope throughout the run:

1. **Complete one Workflow project** — let `workflow-next` select or resume one coherent Issue
   batch, carry that batch through validation and `kaola-workflow-finalize`, then stop.
2. **Recurring Workflow projects** — create or reuse one `foreground: true` scheduler in the same
   Kimi CLI main orchestrator; every firing resumes or completes work inside the authorized project goal.
3. **Complete one PR review and finalization** — use `workflow-next` to review the exact PR, repair
   in-scope defects, then merge and finalize through Kaola Workflow.
4. **Recurring PR review and finalization** — reproduce the tested Automation shape: fresh open-PR
   query, main-orchestrator foreground scheduler, full review, merge, and finalization.

## Select the mode

- **Create, start, or resume project work:** read
  [references/task-modes.md](references/task-modes.md),
  [references/project-run.md](references/project-run.md), and
  [references/kaola-lifecycle.md](references/kaola-lifecycle.md).
- **Inspect progress or report status:** additionally read
  [references/status-monitoring.md](references/status-monitoring.md) and
  [references/codex-supervision.md](references/codex-supervision.md).
- **Send to or stop Kimi CLI:** read [references/platform.md](references/platform.md) and use
  `scripts/runtime-tmux.sh`; do not reconstruct its ownership checks ad hoc.
- **Finalize or close a run:** read [references/closing.md](references/closing.md).
- **Review any PR:** first read
  [references/pr-claim-handoff.md](references/pr-claim-handoff.md), then invoke `workflow-next`
  with the measured claim context and its narrow ignore rule before creating workflow state or
  checking out a writable PR branch.
- **A user decision may be needed:** read
  [references/human-decisions.md](references/human-decisions.md) before prompting Kimi CLI.
- **The user explicitly requested periodic work:** additionally read
  [references/scheduling.md](references/scheduling.md). Do not load or apply it otherwise.

## Essential contract

1. Resolve the repository, exact tmux session, and goal from explicit user input or the bare
   invocation defaults above. Do not infer authorization for a different repository, issue set,
   deployment, or destructive operation.
2. Run `scripts/runtime-tmux.sh preflight --repo <root> --session <name>`. Treat the live adapter preflight result as authority for discovered project instructions and Kaola commands; never apply a
   remembered `CLAUDE.md`, `AGENTS.md`, redirect, plugin layout, or Kimi CLI version as current fact.
3. Start a new Kimi CLI conversation or resume the intended one. If an active Kaola project already
   owns the target, resume its `workflow-state.md` and `mission-list.md` only when this conversation
   is the verified owner or successor. Never adopt another session's folder or duplicate its claim.
   For PR work, classify linked-Issue claims with
   [references/pr-claim-handoff.md](references/pr-claim-handoff.md), then still invoke
   `workflow-next`. An originating PR claim may be ignored as a blocker to review, never as an
   ownership protection.
4. Give the goal to the Kimi CLI **main conversation**. Require it to use `workflow-next`, keep the
   mission list recoverable, and return value-laden or irreversible decisions to that same main
   conversation. A detached subagent may own a bounded mission item, never the project intake.
5. Immediately after a run starts or resumes, create or update one 15-minute Codex thread heartbeat
   for this exact run using [references/codex-supervision.md](references/codex-supervision.md). It
   observes and reports to the user; it is not a Kimi CLI execution loop.
6. Observe without injecting while Kimi CLI is busy. Use Git, the Kaola state files, and fresh forge
   state to distinguish in-progress, waiting-human, ready-to-finalize, finalized, and uncertain.
   Send new input only when the helper reports an
   owned session, the exact repository, a detected Kimi CLI TUI, and `activity: idle`.
7. When every mission in a run this conversation owns is done, instruct the main conversation to
   use `kaola-workflow-finalize`. An origin PR handoff already finalized to a PR sink: finish its
   workflow-driven review with merge and the originating run's `watch-pr`, not a second finalize
   against reconstructed state. If that exact origin state is absent or `watch-pr` cannot settle
   the residue, prove the PR merged and the linked Issues completed, then directly remove only the
   matching claim marker(s) and `workflow:in-progress` label(s); ambiguity requires
   `HUMAN_DECISION_REQUIRED`. Confirm validation, sink, remote state, issue closure or agreed
   keep-open state, zero matching claim residue, archive, and cleanup from evidence rather than
   success prose.
8. Close the selected mode with [references/closing.md](references/closing.md). Stop after this
   explicitly selected batch run. Delete the exact Codex supervision heartbeat when the terminal
   state has been verified. In one-shot mode, do not start a second unrelated batch. Leave an
   active session running unless the user asked to stop it or the owned session is idle and the
   applicable operating agreement says to stop it.

## Required handoff

Report the exact repository, tmux session, Kimi CLI session identity when visible, Codex heartbeat ID,
Git branch/HEAD and cleanliness, Kaola project and issue set, mission counts, forge state, current
activity, completion classification, next action, and any user decision still required.
