# Droid ACP transport

Command: `droid exec --output-format acp`. Login requires a PTY: `true`. Platform quirks: native ACP agent (no bridge, no translator, acp_wrapper_pin empty); config options are declared in the session/new result, never initialize: model, reasoning_effort, autonomy_level (full bypass = auto-high); the default ACP session is already auto-high; the Runner's --permission-mode names translate onto autonomy values over ACP (bypassPermissions/high→auto-high, medium→auto-medium, low→auto-low, manual→normal) because the agent has no mode configId; launch flags do not shape ACP sessions; session/resume preferred and the native session id surfaces in the session/new result and session/list (resume/load do not echo it); auth stays native (device-pairing or FACTORY_API_KEY), never handled by the Runner.

## Command surface

Use `preflight`, `start`, `send`, `steer`, `wait`, `observe`, `capture`, `permit`, `cancel`, and `stop` with the same platform/session/repository identity. `key escape` maps to cancellation; other native keys and editor replacement are PTY-only capabilities. `permit` / `cancel` / `stop` settle each permission `request_id` at most once; a second settler is `unknown-request`.

Humans watch with Terminal or host-wide `list`, session `view`, and local `follow`. Orchestrator ordinary turns must not poll raw frames as a human UI. Where supported, PTY can handle terminal-only login and native TUI takeover; check platform quirks before using it.

## Level-zero receipt

Every receipt identifies `schema_version`, `platform`, `session`, `repo`, `transport`, and Git facts. Mutation receipts also report `mutation_status`, outcome, stop reason, and available protocol events or final text.

`capture` defaults to compact final text. `--tools` includes tool events, `--since EVENT_OFFSET` selects newer events, `--full` includes the complete event record, and `--inline` returns content inline when supported. Every ordinary `capture` receipt (`--lines`, `--since`, `--tools`) is bounded: over budget, the oldest entries are dropped and `truncated` records kept/dropped/total counts, the byte size and sha256 of the untruncated stream, and the `--full` hint; `--full` is the explicit, unbounded request. Ordinary `observe`/`status` receipts are bounded the same way on their own larger `state_receipt_bytes` budget (256 KiB, Issue #64, so a realistic `session_meta` and the stored `record` stay whole and `configOptions` `currentValue` — the configured model — remains readable): scalar facts stay whole, and an over-budget structure (`record`, `session_meta`, `initial_config_options`, `capabilities`, `agent_info`; `pending_permissions` keeps its newest entries) is replaced by its byte size and sha256 under `truncated.fields`.

`mutation_status` is one of `not_started`, `accepted`, `in_progress`, `completed`, or `unknown`. These are transport facts, not permission to retry.

## Steering (`steer`)

Native steering on this platform: **unsupported** (entry ``). No steering entry on the ACP surface: all four candidate methods answer JSON-RPC -32601 on @factory/cli 0.220.0 and `initialize` advertises no steering `_meta`. A second `session/prompt` during a live turn is accepted and both prompts settle `end_turn`, which is concurrent/queued turn handling, not documented active-turn injection; the Runner does not call it steering.

`steer` delivers one Agent-chosen message to the turn **already running** on this exact session,
over the same routing as `send`: no scheduler, no second writer, no second lifecycle. The original
prompt keeps its request id, output, and terminal state, and the receipt's `turn_request_id`,
`turn_request_id_after`, and `turn_request_id_preserved` make that checkable. Content is literal
transport under the same identity, redaction, and bounded-receipt rules as `send`.

`steer_outcome` and `steer_consumed` are the only consumption claims:

| `steer_outcome` | `steer_consumed` | Meaning |
|---|---|---|
| `injected` | `true` | the running turn took the text; adoption by the model is a separate question |
| `started_new_turn` | `true` | the agent opened a separate turn instead — not injection, and this holder does not track it |
| `not_consumed` | `false` | nothing was written (no active turn, or the turn had already settled); `send` a normal prompt if you still want it |
| `unsupported` | `false` | no native entry on this platform or transport; nothing was written |
| `rejected` | `false` | the agent refused the request; `error.detail` carries its reason |
| `unknown` | `null` | no reply or an unrecognized outcome — consumption is undecided; do not resend blindly |

An idle session is never steered: the Runner refuses before writing, since some agents answer an
idle steering call by starting a detached turn. A turn ending in the same instant returns
`not_consumed`, never a silent resend. `steer` is an `acp` operation; over `pty` it answers
`steer-unsupported-transport`, because a mid-turn terminal write is an ordinary keystroke stream
whose meaning only the native UI decides. The Runner never turns a `steer` into `cancel`+`send`,
a transport fallback, or a worker event.

`start` resolves the same tier/model/effort/Fast selection as PTY and applies it through the
agent's advertised `session/set_config_option` IDs — model first, then effort, then Fast — using
`model`/`reasoning_effort`/`` when non-empty.
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
