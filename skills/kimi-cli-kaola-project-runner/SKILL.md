---
name: kimi-cli-kaola-project-runner
description: Use when Codex should communicate with a Kimi Code CLI main conversation through an exact tmux session by starting it, reading evidence, sending Agent-selected prompts or keys, reading replies, and stopping only that session.
---

# Kimi CLI Kaola Project Runner

This Skill is a communication driver for Kimi CLI. It gives the controlling Agent a
measured tmux channel; it does not choose commands, Workflow modes, cadence, state, approvals,
retries, or completion policy.

## Communication loop

Use the canonical Git root and one exact session name throughout:

```bash
REPO="$(git rev-parse --show-toplevel)"
SESSION="kimi-cli-kaola-<purpose>"
scripts/runtime-tmux.sh preflight --repo "$REPO" --session "$SESSION"
scripts/runtime-tmux.sh start --repo "$REPO" --session "$SESSION"
scripts/runtime-tmux.sh observe --repo "$REPO" --session "$SESSION"
scripts/runtime-tmux.sh capture --repo "$REPO" --session "$SESSION" --lines 160
```

`preflight` reports runtime and optional Kaola carrier evidence. Missing Workflow commands,
configuration health, account state, trust state, editor state, activity hints, or a changed
snapshot do not authorize or block starting the CLI communication channel.

After reading current evidence, the controlling Agent chooses what to send:

```bash
scripts/runtime-tmux.sh send --repo "$REPO" --session "$SESSION" --text '<agent-selected prompt>'
scripts/runtime-tmux.sh observe --repo "$REPO" --session "$SESSION"
scripts/runtime-tmux.sh capture --repo "$REPO" --session "$SESSION" --lines 200
```

For a native selection screen, the Agent may choose one exact key. The Runner transfers it without
interpreting its meaning or adding Enter:

```bash
scripts/runtime-tmux.sh key --repo "$REPO" --session "$SESSION" --key down
scripts/runtime-tmux.sh key --repo "$REPO" --session "$SESSION" --key enter
```

Supported key names are `up`, `down`, `left`, `right`, `enter`, `escape`, `tab`, `backtab`, and
`space`. Read the resulting output before choosing another action.

When the Agent decides the exact session is finished, end only that owned session:

```bash
scripts/runtime-tmux.sh stop --repo "$REPO" --session "$SESSION"
scripts/runtime-tmux.sh status --repo "$REPO" --session "$SESSION"
```

Use `--force` only when the Agent explicitly chooses terminal containment for this exact owned
session. Never use raw `tmux send-keys` or broad session/process cleanup.

## Evidence boundary

- `raw_current_frame`, `capture`, process facts, editor facts, approval facts, activity hints, and
  snapshot changes are evidence for the Agent.
- Exact session ownership, platform/repository identity, one-pane targeting, relay attestation,
  literal payload/key fingerprinting, terminal-control rejection, lease serialization, and truthful
  recovery are transport integrity checks.
- The Runner never classifies evidence into permission to act. The Agent handles every runtime or
  Workflow problem after reading the evidence.
- No invocation implicitly starts `workflow-next`, installs commands, materializes repository files,
  creates a heartbeat, or selects recurring behavior. The Agent may send any of those commands when
  it decides they serve the user's task.

See [references/platform.md](references/platform.md) for Kimi CLI launch/observation facts and
[references/transport.md](references/transport.md) for receipt and recovery details.
