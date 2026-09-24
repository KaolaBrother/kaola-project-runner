---
name: dsh-kaola-project-runner
description: Use when the controlling Agent should communicate with a dsh (DeepSeek Harness) main conversation through an exact owned ACP session by starting it, reading evidence, sending Agent-selected prompts or keys, reading replies, and stopping only that session.
---

# dsh Kaola Project Runner

This Skill is a communication driver for dsh. It gives the controlling Agent a
measured ACP channel to one exact owned session; it does not choose commands, Workflow modes, cadence, state, approvals,
retries, or completion policy. The separate Skill `kaola-project-runner` (display name Project
Runner) is the main orchestrator when a host Agent is supervising workers; this Skill stays
transport-only.

## Transport

ACP is the only transport (Issue #130). The ACP command is `dsh --profile acp`; prompts travel over its stdio JSON-RPC, never shell eval. There is no login step (authMethods is empty); a provider route still needs its credential, such as DEEPSEEK_API_KEY. This platform's ACP quirks are in [references/acp.md](references/acp.md) — open it when a quirk matters. A request for the retired PTY transport is refused with `transport-pty-retired` and changes nothing.

| `mutation_status` | Safe interpretation |
|---|---|
| `not_started` | No prompt write began. |
| `accepted` | The agent accepted the prompt. |
| `in_progress` | Work may already be mutating state. |
| `completed` | The turn reached a reported stop reason. |
| `unknown` | Partial mutation cannot be ruled out. |

Runner never auto-falls back or resends, and never restarts or resumes a session on its own. Read the receipt and decide whether another prompt is appropriate.

## Communication loop

Resolve this Skill's installed directory once and call its scripts by absolute path — the install
destination may contain spaces, and the user's project is passed only through `--repo` (relative
paths in these references resolve against the Skill, never the project cwd). Progressive
disclosure: open a reference only when the current operation needs it, run the scripts and never read their source, and prefer bounded
receipts (`observe`, `status`, `capture --lines`) over whole-history dumps — `capture --full` is an
explicit, unbounded request:

```bash
SKILL_DIR="/absolute/path/to/dsh-kaola-project-runner"   # the directory containing this file
REPO="/abs/canonical/root"   # canonical Git root, not a linked worktree
SESSION="<exact-name>"   # under Project Runner: <platform>-<CODE>-i<ISSUE>-<purpose>
"$SKILL_DIR/scripts/runtime-tmux.sh" preflight --repo "$REPO" --session "$SESSION"
"$SKILL_DIR/scripts/runtime-tmux.sh" start --repo "$REPO" --session "$SESSION"
"$SKILL_DIR/scripts/runtime-tmux.sh" observe --repo "$REPO" --session "$SESSION"
"$SKILL_DIR/scripts/runtime-tmux.sh" capture --repo "$REPO" --session "$SESSION" --lines 200
```

The controlling Agent owns model selection for each `start`. This Skill declares its per-run
presets — `--tier default` (**DeepSeek V4.1 Flash (OpenCode Go)**: `opencode-go/deepseek-v4.1-flash`, no Runner effort override); `--tier upgrade` equals default here — and `default` applies whenever the user did
not explicitly choose otherwise. Select `upgrade` only when the user explicitly asks for a stronger
or upgraded model or describes this work as complex; never infer the upgrade from code size,
failures, elapsed time, or your own complexity assessment.

An explicit user model choice always wins: pass it with `--model ID`, adding `--effort LEVEL` only
when the user also named an effort. A bare explicit `--model` leaves the runtime's native effort
alone — never attach a preset's effort to a different model. If the user picks a model ID that
already encodes effort or Fast (such as a `-fast` variant), pass it as-is; the Runner does not
invent extra effort or Fast configuration for it.

Fast is OFF by default. Pass `--fast on` only on an explicit user request for Fast; this platform's
Fast support: no native Fast toggle and no Fast config option on the ACP surface; the catalog's flash-named routes are explicit model choices, not a Fast switch. Fast and tier are independent selections. When a native fast model
ID is what the user explicitly selected, it counts as the explicit Fast selection — report the
conflict honestly if it is also passed with `--fast off`.

`preflight` and `start` report the requested and resolved selection, and `start` what it applied
(`config_application`, `effective_selection`), including unavailable, unsupported, and unknown
outcomes; `observe`/`status` show the agent's `configOptions` `currentValue`. `--resume`/`--continue`
preserve the saved native session model and effort unless the caller supplies `--tier`, `--model`,
or `--effort`; Fast stays a per-run request (off unless explicitly on). All of this is per-run
input and never rewrites global CLI configuration. A mismatch or unreadable actual model remains
evidence for the Agent and does not disable the communication channel.

`preflight` reports runtime and optional Kaola carrier evidence. Missing Workflow commands,
configuration health, account state, activity hints, or a changed
snapshot do not authorize or block starting the CLI communication channel.

Use the evidence internally to choose the next communication action. Do not narrate raw holder,
process, snapshot, model, or activity fields in user progress updates; report only visible
task progress, an actual transport failure, or a decision that genuinely needs the user.

After reading current evidence, the controlling Agent chooses what to send:

```bash
"$SKILL_DIR/scripts/runtime-tmux.sh" send --repo "$REPO" --session "$SESSION" --text '<agent-selected prompt>'
"$SKILL_DIR/scripts/runtime-tmux.sh" observe --repo "$REPO" --session "$SESSION"
"$SKILL_DIR/scripts/runtime-tmux.sh" capture --repo "$REPO" --session "$SESSION" --lines 200
```

## Steering a running turn

dsh's ACP surface exposes no native mid-turn entry, so a bare `steer`
refuses and writes nothing. The available path is the composite, which you
choose explicitly:

```bash
"$SKILL_DIR/scripts/runtime-tmux.sh" steer --repo "$REPO" --session "$SESSION" \
  --steer-mode interrupt --text '<redirection>'
```

It **cancels** the running turn, confirms it stopped, then sends your text as the
next turn on the same session, which keeps the conversation's context. That is
interrupted-then-continued, never injection: work in progress stops and may have
left partial side effects (`side_effects_possible`). An unconfirmed cancel sends
nothing and reports `unknown`. See [references/steering.md](references/steering.md).

## Cancel and permissions

`key --key escape` (or `cancel`) cancels the running turn; there are no other native keys, menus,
or editor replacement. Settle a pending permission `request_id` with
`permit [--request-id ID] --option OPTION_ID` (an option the request offers); omitting `--option`
answers `cancelled`, which denies. Read the resulting output before choosing another action.

Permission default: `start` launches with `DSH_PERMISSION_MODE=danger-full-access` (no Seatbelt sandbox, approval never) unless the caller set that variable; `--permission-mode read-only|workspace-write|danger-full-access` wins over both (bypassPermissions maps to danger-full-access).

When the Agent decides the exact session is finished, end only that owned session:

```bash
"$SKILL_DIR/scripts/runtime-tmux.sh" stop --repo "$REPO" --session "$SESSION"
"$SKILL_DIR/scripts/runtime-tmux.sh" status --repo "$REPO" --session "$SESSION"
```

Use `--force` only when the Agent explicitly chooses forced containment for this exact owned
session. Never use broad session/process cleanup, and never reconstruct ownership from process
names or fuzzy session matches.

## Ending, releasing, and resuming

The controlling Agent owns every completion judgment; the Runner executes the chosen operation
and reports the true result. These are suggestions, never gates:

- A finished reply is not a finished task: an `end_turn` event, an idle terminal, or a
  successful `send` receipt never establishes completion.
- When this delegation's work is delivered and no immediate interaction is expected, the
  default recommendation is to `stop` the exactly-owned running session. Keep it running
  when the Agent expects to resume interacting right away or the user asked for it to stay.
- `stop` releases the owned runtime (the ACP holder and its agent). It never deletes CLI
  history, session records, work artifacts, or unrelated resources. Judge success by the
  `stop`/`status` result evidence, not by a completed call.
- Before stopping, the Agent may keep available resume facts (platform, canonical repo, any
  reported native session ID, outcome, remaining work) from existing receipts and Workflow
  records. The native session ID is the CLI's own conversation identifier, never the Runner's
  `--session` name. Missing identifiers never block a chosen `stop`.
- Later work resumes by the Agent's choice: `start --resume <native-session-id>`,
  `start --continue` for the platform's latest conversation, or a fresh `start` plus existing
  records where the platform cannot resume.

## Optional Kaola Workflow recommendation

For project work, when Kaola Workflow is available to dsh and fits the user's task,
consider telling the user whether you plan to use it. Ordinary Workflow-backed work binds `--repo`
to the consuming project's canonical Git root and asks this CLI to invoke its installed
`workflow-next`, so that runtime's Workflow creates or recovers the child worktree; this Skill only
transports the exact session. Linked-worktree starts, outer-prepared bundles, and existing-run
recovery are Agent decisions, not transport gates. Inspect Git and Workflow evidence first, report
the chosen Git root, and allow several exact sessions at one canonical root with separate Workflow
worktrees. A session already in a child worktree is advisory: preserve work, then continue,
stop/restart at root, or use another Workflow recovery path. Installation for another runtime alone
does not establish availability here; the Agent decides whether to adopt this recommendation.

If adopted, consider supervising `kaola-workflow-finalize` through the selected merge/sync or PR
delivery, verifying the actual result and cleanup of this task's workspace, worktrees, and branches.
PR delivery is not a merged result; preserve resources still needed by an open PR or other active
work. These are suggestions for the Agent, not automatic Runner actions or communication gates.

## Evidence boundary

- `capture`, events, process facts, permission facts, activity hints, and snapshot changes are
  evidence for the Agent.
- Exact session ownership, platform/repository identity, holder identity, prompt fingerprinting,
  and outbound redaction are transport integrity checks.
- The Runner never classifies evidence into permission to act. The Agent handles every runtime or
  Workflow problem after reading the evidence.
- No invocation implicitly starts `workflow-next`, installs commands, materializes repository files,
  creates a heartbeat, or selects recurring behavior. The Agent may send any of those commands when
  it decides they serve the user's task.

See [references/platform.md](references/platform.md) for dsh launch/observation facts
and [references/acp.md](references/acp.md) for the structured ACP command surface.
