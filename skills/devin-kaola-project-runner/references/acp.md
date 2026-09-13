# Devin CLI ACP transport

Command: `devin acp`. Login requires a PTY: `false`. Platform quirks: agent reports affogato 0.0.0-dev; large model option catalog.

## Command surface

Use `preflight`, `start`, `send`, `wait`, `observe`, `capture`, `permit`, `cancel`, and `stop` with the same platform/session/repository identity. `key escape` maps to cancellation; other native keys and editor replacement are PTY-only capabilities. `permit` / `cancel` / `stop` settle each permission `request_id` at most once; a second settler is `unknown-request`.

Humans watch with Terminal or host-wide `list`, session `view`, and local `follow`. Orchestrator ordinary turns must not poll raw frames as a human UI. PTY remains login and native TUI takeover.

## Level-zero receipt

Every receipt identifies `schema_version`, `platform`, `session`, `repo`, `transport`, and Git facts. Mutation receipts also report `mutation_status`, outcome, stop reason, and available protocol events or final text.

`capture` defaults to compact final text. `--tools` includes tool events, `--since EVENT_OFFSET` selects newer events, `--full` includes the complete event record, and `--inline` returns content inline when supported.

`mutation_status` is one of `not_started`, `accepted`, `in_progress`, `completed`, or `unknown`. These are transport facts, not permission to retry.

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
