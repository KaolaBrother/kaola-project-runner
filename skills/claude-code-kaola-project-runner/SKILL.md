---
name: claude-code-kaola-project-runner
description: Use when the controlling Agent should communicate with a Claude Code main conversation through an exact tmux session by starting it, reading evidence, sending Agent-selected prompts or keys, reading replies, and stopping only that session.
---

# Claude Code Kaola Project Runner

This Skill is a communication driver for Claude Code. It gives the controlling Agent a
measured tmux channel; it does not choose commands, Workflow modes, cadence, state, approvals,
retries, or completion policy. The separate Skill `kaola-project-runner` (display name Project
Runner) is the main orchestrator when a host Agent is supervising workers; this Skill stays
transport-only.

## Transport facts

Default transport: **acp**. The ACP command is `node $SKILL_DIR/scripts/vendor/claude-code-acp/dist/index.js`; its known quirks are `vendored pinned fork of harukitosa/claude-code-acp (MIT), never the npm registry package or npx; one claude -p subprocess per turn, later turns pass --resume; the bridge drops ANTHROPIC_API_KEY and ANTHROPIC_AUTH_TOKEN so the subscription login and native Settings resolve inside claude; login itself stays a PTY act`, and login requires a PTY: `true`. Select either channel explicitly with `--transport acp|pty` when the default is not appropriate.

## Cost hints

ACP usually carries structured text and events with less terminal-rendering overhead. Where supported, PTY preserves the native interactive UI and handles terminal-only login or selection flows. These are cost and capability facts; the controlling Agent chooses the transport.

## Fallback

| `mutation_status` | Safe interpretation |
|---|---|
| `not_started` | No prompt write began. |
| `accepted` | The agent accepted the prompt. |
| `in_progress` | Work may already be mutating state. |
| `completed` | The turn reached a reported stop reason. |
| `unknown` | Partial mutation cannot be ruled out. |

Runner never auto-falls back or resends. Read the receipt and let the controlling Agent decide whether another transport or prompt is appropriate.

## Communication loop

Resolve this Skill's installed directory once and call its scripts by absolute path — the install
destination may contain spaces, and the user's project is passed only through `--repo` (relative
paths in these references resolve against the Skill, never the project cwd). Progressive
disclosure: load this Skill only when this platform is selected, open a reference only when the
current operation needs it, run the scripts and never read their source, and prefer bounded
receipts (`observe`, `status`, `capture --lines`) over whole-history dumps — `capture --full` is an
explicit, unbounded request:

```bash
SKILL_DIR="/absolute/path/to/claude-code-kaola-project-runner"   # the directory containing this file
REPO="$(git rev-parse --show-toplevel)"
SESSION="claude-code-kaola-<purpose>"
"$SKILL_DIR/scripts/runtime-tmux.sh" preflight --repo "$REPO" --session "$SESSION"
"$SKILL_DIR/scripts/runtime-tmux.sh" start --repo "$REPO" --session "$SESSION"
"$SKILL_DIR/scripts/runtime-tmux.sh" observe --repo "$REPO" --session "$SESSION"
"$SKILL_DIR/scripts/runtime-tmux.sh" capture --repo "$REPO" --session "$SESSION" --lines 160
```

The controlling Agent owns model selection for each `start`. This Skill declares two per-run
presets — `--tier default` (**Opus High**: `opus`,
effort=high) and `--tier upgrade` (**Fable High**:
`fable`, effort=high) — and `default` applies whenever the user did
not explicitly choose otherwise. Select `upgrade` only when the user explicitly asks for a stronger
or upgraded model or describes this work as complex; never infer the upgrade from code size,
failures, elapsed time, or your own complexity assessment.

An explicit user model choice always wins: pass it with `--model ID`, adding `--effort LEVEL` only
when the user also named an effort. A bare explicit `--model` leaves the runtime's native effort
alone — never attach a preset's effort to a different model. If the user picks a model ID that
already encodes effort or Fast (such as a `-fast` variant), pass it as-is; the Runner does not
invent extra effort or Fast configuration for it.

Fast is OFF by default. Pass `--fast on` only on an explicit user request for Fast; this platform's
Fast support: Fast via process-scoped `--settings '{"fastMode": ...}'` at launch: `--fast on` passes fastMode=true, `--fast off` pins fastMode=false for the session; the native CLI determines model support — effective stays unknown without native evidence and the selected model is never changed. Fast and tier are independent selections. When a native fast model
ID is what the user explicitly selected, it counts as the explicit Fast selection — report the
conflict honestly if it is also passed with `--fast off`.

`preflight`, `start`, `observe`, and `status` report requested, resolved, configured, and actual
model evidence, including unavailable, unsupported, and unknown outcomes. `--resume`/`--continue`
preserve the saved native session model and effort unless the caller supplies `--tier`, `--model`,
or `--effort`; Fast stays a per-run request (off unless explicitly on). All of this is per-run
input and never rewrites global CLI configuration. A mismatch or unreadable actual model remains
evidence for the Agent and does not disable the communication channel.

`preflight` reports runtime and optional Kaola carrier evidence. Missing Workflow commands,
configuration health, account state, trust state, editor state, activity hints, or a changed
snapshot do not authorize or block starting the CLI communication channel.

Use the evidence internally to choose the next communication action. Do not narrate raw relay,
process, snapshot, model, editor, or activity fields in user progress updates; report only visible
task progress, an actual transport failure, or a decision that genuinely needs the user.

After reading current evidence, the controlling Agent chooses what to send:

```bash
"$SKILL_DIR/scripts/runtime-tmux.sh" send --repo "$REPO" --session "$SESSION" --text '<agent-selected prompt>'
"$SKILL_DIR/scripts/runtime-tmux.sh" observe --repo "$REPO" --session "$SESSION"
"$SKILL_DIR/scripts/runtime-tmux.sh" capture --repo "$REPO" --session "$SESSION" --lines 200
```

For a native selection screen, the Agent may choose one exact key. The Runner transfers it without
interpreting its meaning or adding Enter:

```bash
"$SKILL_DIR/scripts/runtime-tmux.sh" key --repo "$REPO" --session "$SESSION" --key down
"$SKILL_DIR/scripts/runtime-tmux.sh" key --repo "$REPO" --session "$SESSION" --key enter
```

Supported key names are `up`, `down`, `left`, `right`, `enter`, `escape`, `tab`, `backtab`, and
`space`. Read the resulting output before choosing another action.

When the Agent decides the exact session is finished, end only that owned session:

```bash
"$SKILL_DIR/scripts/runtime-tmux.sh" stop --repo "$REPO" --session "$SESSION"
"$SKILL_DIR/scripts/runtime-tmux.sh" status --repo "$REPO" --session "$SESSION"
```

Use `--force` only when the Agent explicitly chooses terminal containment for this exact owned
session. Never use raw `tmux send-keys` or broad session/process cleanup.

## Ending, releasing, and resuming

The controlling Agent owns every completion judgment; the Runner only executes the chosen
operation and reports the true result. These are suggestions, never gates:

- A finished reply is not a finished task. An `end_turn` event, an idle terminal, or a
  successful `send` receipt never establishes completion; the Agent reads the result and
  decides whether to continue, review, fix, or end.
- When this delegation's work is delivered and no immediate interaction is expected, the
  default recommendation is to `stop` the exactly-owned running session. Keep it running
  when the Agent expects to resume interacting right away or the user asked for it to stay.
- `stop` releases the owned runtime (PTY child/relay/tmux session, or ACP holder/agent). It
  does not delete CLI history, session records, work artifacts, or unrelated resources, and
  it is never coupled to a history wipe. Judge success by the `stop`/`status` result
  evidence, not by a completed call.
- Before stopping, the Agent may keep whatever resume facts are already available —
  platform, canonical repo, any reported native session ID, outcome, and remaining work —
  reusing existing receipts and Workflow records. The native session ID is the CLI's own
  conversation identifier and is not the Runner's tmux session name. Missing identifiers
  never block a chosen `stop`; nothing here is a required checkpoint.
- Later work resumes through the Agent's choice: `start --resume <native-session-id>` when
  an exact identifier is known, `start --continue` to let the platform pick its latest
  conversation, or a fresh `start` plus existing work records when the platform cannot
  resume. The Runner never auto-falls back, resends an old prompt, or restarts on its own.

## Optional Kaola Workflow recommendation

For project work, when Kaola Workflow is available to Claude Code and fits the user's task,
consider telling the user it is available and whether you plan to use it, then asking the CLI to
start or resume with `workflow-next` using its installed native Workflow instructions. Existing
carrier evidence can help; installation for another runtime alone does not establish availability
here. The controlling Agent decides whether to adopt this recommendation, including for diagnosis
or ordinary CLI tasks.

If adopted, consider supervising `kaola-workflow-finalize` through the selected merge/sync or PR
delivery, verifying the actual result and cleanup of this task's workspace, worktrees, and branches.
PR delivery is not a merged result; preserve resources still needed by an open PR or other active
work. These are suggestions for the Agent, not automatic Runner actions or communication gates.

## Evidence boundary

- `raw_current_frame`, `capture`, process facts, editor facts, approval facts, activity hints, and
  snapshot changes are evidence for the Agent.
- Exact session ownership, platform/repository identity, one-pane targeting, relay attestation,
  literal payload/key fingerprinting, and terminal-control rejection are transport integrity checks.
- The Runner never classifies evidence into permission to act. The Agent handles every runtime or
  Workflow problem after reading the evidence.
- No invocation implicitly starts `workflow-next`, installs commands, materializes repository files,
  creates a heartbeat, or selects recurring behavior. The Agent may send any of those commands when
  it decides they serve the user's task.

See [references/platform.md](references/platform.md) for Claude Code launch/observation facts,
[references/transport.md](references/transport.md) for PTY receipt and recovery details, and
[references/acp.md](references/acp.md) for the structured ACP command surface.
