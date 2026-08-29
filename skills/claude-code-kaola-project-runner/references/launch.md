# Measured Claude Code launch flow

Use this sequence for every fresh Claude Code main conversation. It is the maintained form of the
live flow that reached Workflow intake successfully; do not reproduce its former raw-tmux repairs.

## 1. Resolve and preflight

Resolve the canonical Git root and exact session name, then run:

```bash
scripts/runtime-tmux.sh preflight --repo "$REPO" --session "$SESSION"
```

Proceed only when the result is `ready` and both `workflow_next` and
`kaola_workflow_finalize` are true. Preserve an existing foreign, mismatched, multi-pane, or
otherwise non-reusable session and report the refusal; never renumber its windows, rewrite its
title, or launch Claude with raw `tmux send-keys`.

## 2. Start with an explicit execution profile

A fresh start defaults to the measured project-run profile:

```bash
scripts/runtime-tmux.sh start --repo "$REPO" --session "$SESSION"
```

That is equivalent to:

```bash
scripts/runtime-tmux.sh start --repo "$REPO" --session "$SESSION" \
  --model opus --effort high --permission-mode auto
```

`auto` is the autonomous project-run mode that successfully crossed ordinary Claude tool approval
prompts. It is not `bypassPermissions`, and it never authorizes Claude to answer
`HUMAN_DECISION_REQUIRED` or to exceed the user's repository and workflow authority. Use
`bypassPermissions` only when the user explicitly requests that exact Claude permission mode; never
reach any permission mode by cycling TUI keys.

An explicit user model, effort, or permission mode overrides the defaults. The carrier validates
model syntax and the supported effort and permission-mode values before creating tmux. Continue or
resume through the same control plane:

```bash
scripts/runtime-tmux.sh start --repo "$REPO" --session "$SESSION" --continue \
  --model "$MODEL" --effort "$EFFORT" --permission-mode "$PERMISSION_MODE"
scripts/runtime-tmux.sh start --repo "$REPO" --session "$SESSION" --resume "$CLAUDE_SESSION_ID" \
  --model "$MODEL" --effort "$EFFORT" --permission-mode "$PERMISSION_MODE"
```

## 3. Verify the live main conversation

Run both status and capture before sending Workflow intake:

```bash
scripts/runtime-tmux.sh status --repo "$REPO" --session "$SESSION"
scripts/runtime-tmux.sh capture --repo "$REPO" --session "$SESSION" --lines 120
```

Require all of the following:

- `owned`, `platform_match`, `repo_match`, `process_match`, and `tui_detected` are true;
- `pane_count` is 1 and `pane_id` is present; window and pane indexes are not authority;
- `pane_process` contains the requested model, effort, and permission-mode launch arguments;
- the visible Claude footer agrees with the requested model/effort when it exposes them;
- `activity` is `idle` before intake.

Claude may replace the terminal title with the active task. That title change is normal and must not
be repaired manually; exact process identity plus stable Claude CLI surfaces remain the TUI proof.

If status is `waiting-human`, do not send. Native Claude trust or tool-approval screens and
`HUMAN_DECISION_REQUIRED` are all non-idle boundaries. Surface the visible decision. A fresh
`--permission-mode auto` session should not stop on routine tool approvals; if it does, preserve the
session and report the discrepancy rather than selecting an approval option automatically.

The decision gate is based on compound current-frame evidence, not on a prompt glyph or an arbitrary
waiting sentence alone. When a pending Workflow decision remains visible together with an editor,
whether empty or populated, status stays `waiting-human` and `send` fails closed even if the original
structured marker has left the short activity tail. After the human answer reaches the exact owned
pane, require enough later runtime output to replace the pending evidence in that tail and then a
fresh empty prompt before treating the conversation as idle. Old marker history outside the current
activity tail does not permanently latch a resumed conversation.

## 4. Send one intake prompt and supervise

Send the one-shot prompt from [project-run.md](project-run.md) only after the verified idle state:

```bash
scripts/runtime-tmux.sh send --repo "$REPO" --session "$SESSION" < prompt.txt
```

Then observe without injecting while `activity` is `busy` and follow the caller-selected cadence.
When a Codex heartbeat is selected for observation only, it reads the exact session, Git, Kaola
state, and forge state without triggering work. When it is selected as the execution carrier, it
follows [scheduling.md](scheduling.md) and starts no later firing before the current one reaches its
recorded terminal, waiting-human, or uncertain boundary. Neither role answers approval prompts.

## 5. Close the exact batch

After every mission is done, use `kaola-workflow-finalize` in this same Claude main conversation.
Only after validation, sink, remote/Issue truth, claim cleanup, archive, Git cleanliness/alignment,
and idle state are verified may the exact session be stopped through `runtime-tmux.sh`. Never infer
completion from an absent pane or a Claude success sentence.
