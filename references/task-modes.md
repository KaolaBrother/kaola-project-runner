# Four Codex task modes

These are Skill-level capabilities exposed to Codex. They are not shell subcommands. Codex selects
one mode, uses the low-level tmux helper where useful, and operates the Grok CLI main conversation
as the current task requires.

## 1. Complete one Workflow project

Use when the user asks Grok to establish, resume, or finish one bounded project goal.

- Start or reuse the exact owned tmux/Grok main conversation.
- Send the one-shot project prompt from [project-run.md](project-run.md).
- Require `workflow-next` to establish or resume the Issue-scoped run and mission list.
- Let the main conversation progress the mission frontier and surface user decisions.
- When every mission is done, require `kaola-workflow-finalize` and verify the terminal state.
- Do not create a Grok scheduler and do not auto-claim another project.

## 2. Recurring Workflow projects

Use only when the user asks Grok to advance project work repeatedly.

- Start or reuse the exact owned Grok main conversation.
- Inspect `/tasks` in the idle main conversation before changing scheduler state.
- Ask with ordinary natural language for exactly one scheduler at the requested interval with
  `foreground: true`; never send `/loop`.
- Every firing must be a new turn in the same main orchestrator, resume active Kaola work first,
  remain inside the authorized project goal, use `workflow-next`, and use
  `kaola-workflow-finalize` when the current run is complete.
- Require authoritative scheduler ID/count/interval/foreground evidence and zero detached intake
  loops or agents.

Read [scheduling.md](scheduling.md) for creation, migration, and verification details.

## 3. Complete one PR review and finalization

Use when the user names one PR or asks for one bounded PR review/merge run. First apply
[pr-claim-handoff.md](pr-claim-handoff.md), then invoke `workflow-next` with the claim class and its
review-only ignore boundary.

Send this core instruction in the Grok main conversation, expanded with the exact repo, number, URL,
and completion boundary:

```text
Use workflow-next to review PR #{number}. Explain the measured linked-Issue claim before startup.
If this is an ORIGIN_PR_HANDOFF and workflow-next reports target_set_conflicts_active_work or an
equivalent claim refusal, ignore that conflict only as a blocker to the PR review: claim:none stays
authoritative, do not claim again, and do not adopt or reconstruct the author's run. Inspect fresh
PR and linked Issue truth, the complete diff, comments, checks, merge state, local validation,
documentation, and Kaola ownership. Repair only in-scope PR defects within the authorized review
handoff and do not merge based only on MERGEABLE or green prose. This main conversation owns review
intake and user decisions, not the originating Issue claim. Stop after this PR's review handoff.
```

For an unclaimed PR, use `kaola-workflow-finalize` normally when every mission is complete. For an
origin PR handoff, merge only after the workflow-driven review passes, then use the existing run's
`watch-pr` cleanup when locally available; do not run a second finalization against reconstructed
author state. Do not create a Grok scheduler for this mode.

## 4. Recurring PR review and finalization

Use when the user asks for the tested open-PR intake behavior.

- Inspect `/tasks`, migrate only an inactive old detached loop, and ensure exactly one scheduler.
- Create it through an ordinary main-conversation request with the requested interval and
  `foreground: true`; never use `/loop`.
- Use the `MAIN_THREAD_PR_INTAKE_V3_WORKFLOW_REVIEW_HANDOFF` contract in
  [scheduling.md](scheduling.md): query open PRs fresh,
  return `NO_OPEN_PRS` without mutation when empty, process non-draft PRs deterministically, and
  classify claims before invoking `workflow-next` for every PR. For an origin PR handoff, tell
  `workflow-next` to ignore the expected claim refusal for review only while preserving
  `claim:none`; use merge plus `watch-pr` rather than a second author-run finalization.
- A firing that requires the user prints `HUMAN_DECISION_REQUIRED` in the main orchestrator and
  prevents later firings from duplicating that blocked run.
- Verify a real firing appears as a new turn in the same Grok conversation, with zero detached
  General-loop scheduler and zero detached intake subagent.

## Supervision shared by all four

After any mode starts or resumes, Codex establishes one 15-minute current-thread heartbeat from
[codex-supervision.md](codex-supervision.md). The heartbeat checks Grok, Git, Kaola, and forge state
and reports to the user until the terminal state is verified, then deletes itself.
