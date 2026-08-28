# Project run

Use this reference to create, start, or resume a project run. Scheduling is a separate, optional
mode.

## Bare Skill invocation

When the user supplies only `$grok-kaola-project-runner`, proceed without a clarification round:

- resolve `repo` as the canonical Git top-level containing the current working directory;
- select the one-shot Workflow project mode;
- derive `session` as `grok-kaola-<repo-basename>` with unsafe tmux-name characters replaced by
  `-`;
- set `goal` to `advance the workflow-selected project to its verified terminal state`;
- set `targets` to `select under workflow-next`;
- use current repository validation, documentation, forge, and Kaola lifecycle requirements as the
  definition of done and authority boundary;
- preflight, start or reuse the exact owned Grok main conversation, and send the start prompt as
  soon as the main conversation is ready for input.

These defaults do not authorize leaving the current repository, starting recurring execution, or
answering an irreversible or value-laden decision for the user. Extra prompt text refines the
defaults but is not required to start.

## Establish the run

Resolve these fields from the user's request and live repository evidence:

- `repo`: absolute Git repository root.
- `session`: exact tmux session name chosen for this project run.
- `goal`: concrete outcome, not a recurring schedule.
- `targets`: user-named issues or PRs; otherwise let `workflow-next` select under its own contract.
- `definition_of_done`: validation, review, documentation, remote, and lifecycle evidence expected.
- `authority_boundary`: mutations authorized by the user and decisions that must come back.

Do not silently broaden a review request into unrelated implementation or let an active directory's
issue replace a user-named target.

If the user described new work but named no Issue, tell Grok to let `workflow-next` resolve it to an
existing Issue or establish the task under its current contract before claiming. The controlling
Agent does not invent parallel bookkeeping outside Kaola Workflow.

## Start prompt

Send this as one prompt to an idle, owned Grok main conversation, adapting only the placeholders:

```text
Work in this Grok main conversation as the owner of the project run.

Repository: {repo}
Goal: {goal}
Target issues or PRs: {targets or "select under workflow-next"}
Definition of done: {definition_of_done}
Authority boundary: {authority_boundary}

Use workflow-next to start or resume this work. First inspect current repository instructions and
current Kaola Workflow state. Reuse an existing active run for these targets rather than creating a
duplicate claim. Maintain mission-list.md as the recovery record. Perform the required work,
review, validation, documentation, and evidence collection.

This main conversation owns project intake and synthesis. You may use bounded subagents for
individual mission items when appropriate, but do not hand the project to a detached General loop
or detached subagent.

When an irreversible or value-laden decision requires the user, return HUMAN_DECISION_REQUIRED in
this main conversation with the evidence, recommendation, and safe options, then wait.

After every mission is complete, use kaola-workflow-finalize. Verify the actual sink, remote state,
issue state, archive, and cleanup before reporting completion. Stop after this selected run; do not
claim another issue automatically.
```

For PR review, make the goal explicit:

```text
Use workflow-next to review PR #{number}. Review the PR, linked issue, full diff, validation
evidence, documentation, and lifecycle state. If it is ready, use kaola-workflow-finalize to finish
the owned run; do not equate mergeable status or green prose with completed review.
```

## Resume prompt

Before sending, observe the session and inspect the promised output locators. Then use:

```text
Resume the existing Kaola Workflow run for {targets}. Read workflow-state.md and mission-list.md
top to bottom. Reconcile in-flight items from their output locators, continue the actual frontier,
and preserve completed mission results. Keep project ownership and any user decision in this main
conversation.
```

Do not create a second run merely because the original worker or terminal is no longer visible.
