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

Default transport: **pty**. The ACP command is `npx --yes @agentclientprotocol/claude-agent-acp@0.18.0`; its known quirks are `pinned wrapper fetched but exited before initialize (probe-eof); PTY login requirement remains`, and login requires a PTY: `true`. Select either channel explicitly with `--transport acp|pty` when the default is not appropriate.

## Cost hints

ACP usually carries structured text and events with less terminal-rendering overhead. PTY preserves the native interactive UI and is required for terminal-only login or selection flows. These are cost and capability facts; the controlling Agent chooses the transport.

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
paths in these references resolve against the Skill, never the project cwd). When this worker is
embedded as a supporting resource under a host Skill's `workers/<platform id>/` directory (this
file is then named `WORKER.md`), SKILL_DIR is that worker directory — not the host Skill root and
not another worker:

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

## Grok Bot account-private form

This document is the account-private Skill `claude-code-kaola-project-runner` for the Grok Bot
host: one single Markdown (frontmatter `name` and `description` plus this body) saved on
its own by the Bot's skill write. It depends on no other saved Skill and on no file tree
in the account; the three reference documents linked above are bundled verbatim at the
end of this document. The scripts run on **Local Computer** (never on the cloud Agent
Computer) from the generated runtime copy installed on this machine by
`./scripts/install-local.sh --runtime grok-bot`:

```bash
SKILL_DIR="${KAOLA_GROK_BOT_HOME:-$HOME/.kaola/grok-bot}/skills/kaola-project-runner/workers/claude-code"
"$SKILL_DIR/scripts/runtime-tmux.sh" preflight --repo "$REPO" --session "$SESSION"
```

`KAOLA_GROK_BOT_HOME` overrides the root `$HOME/.kaola/grok-bot`. In that copy this
contract is the file `workers/claude-code/WORKER.md` and `$SKILL_DIR/references/` holds the
same three documents. The main Skill `kaola-project-runner` (Project Runner) selects
this worker by its Skill name; this Skill stays transport-only and carries no
orchestrator policy.

## Bundled reference: references/platform.md

# Claude Code adapter

- Platform ID: `claude-code`
- Default binary: `claude`
- Binary override: `CLAUDE_BIN`
- Default tmux session prefix: `claude-code-kaola`
- Continue: `--continue`
- Exact resume: `--resume <session-id>`
- Runner default preset (`--tier default`): **Opus High** — `opus` with `effort=high`
- Runner upgrade preset (`--tier upgrade`): **Fable High** — `fable` with `effort=high`
- Fast support: Fast via process-scoped `--settings '{"fastMode": ...}'` at launch: `--fast on` passes fastMode=true, `--fast off` pins fastMode=false for the session; the native CLI determines model support — effective stays unknown without native evidence and the selected model is never changed

## Preflight

Verify the Claude executable and report optional Kaola carrier and launch-option evidence without gating communication.

Preflight is read-only. Optional Kaola/Workflow surfaces and runtime health are reported as evidence;
their absence does not block starting the CLI. The Runner never installs, upgrades, adopts, or
rewrites runtime configuration.

Model catalogs are probed read-only. Selection precedence is explicit `--model` over the chosen
`--tier` preset; explicit `--effort` overrides preset effort only on the model it was given with,
and a different explicit model without explicit effort leaves native effort untouched. Encoded
effort/Fast model IDs are not followed by invented extra configuration calls. Saved picker/config
values never become the Runner default; on `--resume`/`--continue` the saved native selection is
preserved unless the caller supplies tier/model/effort, while Fast stays a per-run request. If the
requested model is absent from or unknown to the readable catalog, the exact declared literal is
still launched and the catalog fact is reported. Actual-model mismatch or unreadable evidence never
blocks ordinary observe, capture, send, key, or stop transport chosen by the Agent.

## Launch

Launch Claude from the canonical repository root with --permission-mode bypassPermissions (default). ACP start sets mode=bypassPermissions after a working initialize; the pinned wrapper remains probe-eof.

Use `"$SKILL_DIR/scripts/runtime-tmux.sh"` for every preflight, start, observe, status, capture,
send, key, answer, and stop operation, where `SKILL_DIR` is the absolute path of the installed Skill
directory containing SKILL.md (quote it — the destination may contain spaces). Read
[transport.md](transport.md) before any action that can change the runtime.
Do not reconstruct ownership checks from process names or fuzzy tmux matches.

Runner `--continue` and `--resume` select the native continuation/resume syntax listed above;
adapters translate these options for the platform. The native session ID is the CLI's own
conversation identifier, distinct from the Runner's tmux session name. What a platform persists and can resume is its own verified behavior, not a
universal Runner promise; when exact resume is unavailable or ambiguous, the Agent chooses
`--continue`, a new session, or existing work records. `stop` releases only the owned runtime
resources and never deletes platform history.

## Measured interaction loop

Start from `observe` and read the complete `raw_current_frame` together with exact tmux, process,
relay, input/output and repository evidence. The Runner does not classify this runtime for the
Agent. The Agent decides whether to wait, send a prompt, transfer a native key, use a tested
whole-editor replace/clear route, open a clean conversation, or surface a human decision.

Transfer the chosen prompt with `send`; an optional snapshot only correlates the receipt. Then
immediately `observe` and `capture` again to read the runtime's actual response. Give retained editor
text and other changed evidence to the Agent rather than blocking the action. If the Agent chose a
Workflow task, it separately verifies the relevant durable repository and forge state. Native key
sequences are transported only after the Agent reads the current screen and names the key.

No launch selects scheduling or recurring behavior. Reported recurring capability is evidence only;
the Agent chooses any execution carrier and cadence outside this Runner.

## Bundled reference: references/transport.md

# Managed Claude Code transport

The Runner starts the runtime as the exact child of a managed nested-PTY relay. A pre-relay session
may still be reported as `legacy-direct`; a running older relay remains readable but reports
`relay-upgrade-required` for mutation. The controlling agent chooses whether and when to restart only
that exact session at a safe boundary.

## Discover and give the evidence to the agent

`SKILL_DIR` below is the absolute path of the installed Skill directory containing SKILL.md; quote it
because the destination may contain spaces.

```bash
"$SKILL_DIR/scripts/runtime-tmux.sh" observe --repo "$REPO" --session "$SESSION"
"$SKILL_DIR/scripts/runtime-tmux.sh" capture --repo "$REPO" --session "$SESSION" --lines 160
```

Read `raw_current_frame`, terminal coordinates, editor and approval observations, process/relay facts,
input/output offsets, Git facts, and any Workflow/forge evidence together. These are observations, not
Runner-owned state or authorization. The Skill does not decide whether the runtime is idle, busy,
waiting, complete, holding a draft, asking for approval, or safe to mutate. The controlling agent
decides what the evidence means and which action to take.

An observation may contain `snapshot_id` and `pane_revision` so later receipts can correlate an action
with what the agent previously saw. They are evidence identifiers, not freshness gates. A normal redraw,
new output, editor change, approval screen, process change, or Git/Workflow change is reported rather
than converted into `stale-snapshot` refusal.

Compatibility fields such as `activity_hint`, `editor_state`, `native_approval`,
`structured_decision_marker`, visible worker counts, and evidence flags may help the agent notice facts.
They never independently permit or prevent an agent-directed `send` or `stop`.

## Transfer the agent's prompt

After the agent chooses the prompt, transfer it directly:

```bash
"$SKILL_DIR/scripts/runtime-tmux.sh" send --repo "$REPO" --session "$SESSION" < prompt.txt
```

The optional legacy `--if-snapshot "$SNAPSHOT_ID"` argument only links the receipt to the earlier
observation as an optional action-time identifier. The compact receipt echoes it as `based_on_snapshot`;
the Runner does not recapture it as a freshness decision and still performs the requested transport when
the relay can mechanically do so. Changed evidence is reported as `observation_changed:true`, not refused.

The relay performs one direct literal or bracketed-paste transfer and attests the payload fingerprint.
It does not stop the runtime child, disable pane input, acquire a lease, run a terminal fence, judge the
runtime prose, or decide whether the prompt was appropriate. Shell metacharacters remain literal input
rather than shell commands.

If the frame contains retained text, an approval, a trust/login screen, active output, or a human
decision, show it to the agent. The agent may still choose to send, use a tested whole-editor replacement,
start/resume a clean conversation, wait, or ask the user. The Skill does not turn any of those
observations into a policy gate.

## Transfer an Agent-selected native key

When a visible native selection screen needs a key, the Agent reads the screen and chooses one:

```bash
"$SKILL_DIR/scripts/runtime-tmux.sh" key --repo "$REPO" --session "$SESSION" --key up
"$SKILL_DIR/scripts/runtime-tmux.sh" key --repo "$REPO" --session "$SESSION" --key enter
```

The Runner accepts `up`, `down`, `left`, `right`, `enter`, `escape`, `tab`, `backtab`, or `space`.
It sends only the selected key bytes, adds no Enter, and attests their fingerprint. It neither infers
the option meaning nor chooses the key. Observe/capture again after every key.

## Read the response and verify durable evidence

After every transfer, observe and capture again:

```bash
"$SKILL_DIR/scripts/runtime-tmux.sh" observe --repo "$REPO" --session "$SESSION"
"$SKILL_DIR/scripts/runtime-tmux.sh" capture --repo "$REPO" --session "$SESSION" --lines 160
```

The Agent reads the real response and decides what happened. Enter or a successful transfer receipt is
not semantic success. If the Agent chose Workflow work, inspect the applicable durable Workflow, Git,
forge, validation, and cleanup evidence separately.

## Stop and capability-specific actions

An agent-directed ordinary stop does not require a snapshot and is not gated by activity, editor,
approval, decision, process-count, coordinate, prose, Git, or Workflow interpretations:

```bash
"$SKILL_DIR/scripts/runtime-tmux.sh" stop --repo "$REPO" --session "$SESSION"
```

`stop` releases exactly the owned PTY child, relay, and tmux session, then reports the actual
exit result; `status` confirms absence afterward. Stopping never deletes CLI history, session
records, or work artifacts — a later `start --resume`/`--continue` or a fresh session is the
Agent's separate choice, using identifiers preserved in earlier receipts when available.

`answer --replace-editor` is a tested whole-editor transport capability where an adapter implements it;
decision and snapshot identifiers are optional correlation evidence. An adapter that lacks that
mechanical capability reports `answer-unsupported`, after which the agent chooses another route.

The transport reports objective facts when it cannot mechanically complete the requested operation,
such as an absent exact session, unavailable or legacy relay, rejected literal input, disconnect, or
unknown transfer outcome. It reports those concrete facts without assigning semantic runtime state.

Payload and answer bytes are transferred as text, not terminal programs. If the relay cannot represent
a payload literally (for example unsupported terminal controls or multiline input without bracketed
paste), it reports that mechanical limitation before a partial write. This is a transport outcome, not
a runtime-status gate.

If a connection is lost before a direct-transfer receipt, partial mutation may be impossible to rule
out. The receipt then reports `mutation_performed:null`; it does not invent a successful recovery or
block later Agent judgment behind restoration metadata.

## Bundled reference: references/acp.md

# Claude Code ACP transport

Command: `npx --yes @agentclientprotocol/claude-agent-acp@0.18.0`. Login requires a PTY: `true`. Platform quirks: pinned wrapper fetched but exited before initialize (probe-eof); PTY login requirement remains.

## Command surface

Use `preflight`, `start`, `send`, `wait`, `observe`, `capture`, `permit`, `cancel`, and `stop` with the same platform/session/repository identity. `key escape` maps to cancellation; other native keys and editor replacement are PTY-only capabilities. `permit` / `cancel` / `stop` settle each permission `request_id` at most once; a second settler is `unknown-request`.

Humans watch with Terminal or host-wide `list`, session `view`, and local `follow`. Orchestrator ordinary turns must not poll raw frames as a human UI. PTY remains login and native TUI takeover.

## Level-zero receipt

Every receipt identifies `schema_version`, `platform`, `session`, `repo`, `transport`, and Git facts. Mutation receipts also report `mutation_status`, outcome, stop reason, and available protocol events or final text.

`capture` defaults to compact final text. `--tools` includes tool events, `--since EVENT_OFFSET` selects newer events, `--full` includes the complete event record, and `--inline` returns content inline when supported.

`mutation_status` is one of `not_started`, `accepted`, `in_progress`, `completed`, or `unknown`. These are transport facts, not permission to retry.

`start` resolves the same tier/model/effort/Fast selection as PTY and applies it through the
agent's advertised `session/set_config_option` IDs — model first, then effort, then Fast — using
``/``/`` when non-empty.
A manifest may declare `acp_init_meta` (`key=value` pairs sent as `clientCapabilities._meta`
during `initialize`): agents that negotiate a parameterized model picker advertise separate
`model`/`effort`/`fast` options with base model IDs and string `true`/`false` fast values instead
of fixed variant descriptors. When a manifest declares `acp_model_map`, a resolved PTY picker ID decomposes onto
the ACP model value the agent advertises for the same model — effort encoded in the picker ID
suffix then travels through the effort option and Fast through the fast option (values converted
per `acp_fast_values`), recorded as `requested_id`/`mapped`/`declared` in the model application.
Model semantics are never substituted: an unmapped ID is sent literally and its rejection is
reported as a limitation. `config_application` records each attempted option's requested value and
applied result; `configured_options` carries the adapter's returned receipts. An option with no
advertised config ID, or one the adapter rejects, is reported as a limitation — the session stays
usable. The `fast` receipt's `effective` reflects proven native state only: a rejected fast option
or an unapplied fast-variant model ID reports `unknown`, and an applied model value's own
descriptor (e.g. `[..,fast=true]`) is reported as the effective fast evidence with any request
conflict noted — never a false on/off.

## Ending and resuming an ACP session

A turn reaching `end_turn` is a reply boundary, not task completion; the Agent judges from the
result whether work continues. When the Agent chooses `stop`, the Runner sends `session/close`
when the adapter advertises that capability, then exits the exactly-owned holder and agent
processes and reports actual exit plus any residue. `stop` does not call `session/delete`,
wipe CLI-side history, or imply the adapter persisted anything — a platform's resume and
history behavior stands on its own verified capability, not on the close call's name. If
in-flight work exists when the Agent has already chosen to stop, the existing `cancel`/exit
path applies.

To resume later work, the Agent chooses `start --resume <session-id>` (the Runner uses
`session/resume` or `session/load` per the advertised capability) or `start --continue`,
which selects the latest `session/list` entry for the repository's canonical cwd. Neither is
guaranteed by the protocol universally; when a platform cannot resume or history is
unavailable, the Agent starts a fresh session and continues from existing work records. The
Runner never auto-resumes, retries an old prompt, or continues a Workflow on its own.
