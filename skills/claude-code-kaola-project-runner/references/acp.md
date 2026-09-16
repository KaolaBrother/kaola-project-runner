# Claude Code ACP transport

Command: `npx --yes @agentclientprotocol/claude-agent-acp@0.18.0`. Login requires a PTY: `true`. Platform quirks: pinned wrapper fetched but exited before initialize (probe-eof); PTY login requirement remains.

## Command surface

Use `preflight`, `start`, `send`, `wait`, `observe`, `capture`, `permit`, `cancel`, and `stop` with the same platform/session/repository identity. `key escape` maps to cancellation; other native keys and editor replacement are PTY-only capabilities. `permit` / `cancel` / `stop` settle each permission `request_id` at most once; a second settler is `unknown-request`.

Humans watch with Terminal or host-wide `list`, session `view`, and local `follow`. Orchestrator ordinary turns must not poll raw frames as a human UI. PTY remains login and native TUI takeover.

## Level-zero receipt

Every receipt identifies `schema_version`, `platform`, `session`, `repo`, `transport`, and Git facts. Mutation receipts also report `mutation_status`, outcome, stop reason, and available protocol events or final text.

`capture` defaults to compact final text. `--tools` includes tool events, `--since EVENT_OFFSET` selects newer events, `--full` includes the complete event record, and `--inline` returns content inline when supported. Every ordinary `capture` receipt (`--lines`, `--since`, `--tools`) is bounded: when it would exceed the shared capture budget, the oldest entries are dropped and `truncated` records kept/dropped/total counts, the byte size and sha256 of the untruncated stream, and the `--full` hint; `--full` is the explicit, unbounded request. Ordinary `observe`/`status` receipts share that budget: scalar facts stay whole, and an over-budget structure (`record`, `session_meta`, `initial_config_options`, `capabilities`, `agent_info`; `pending_permissions` keeps its newest entries) is replaced by its byte size and sha256 under `truncated.fields`.

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
