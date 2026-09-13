# Kimi CLI ACP transport

Command: `kimi acp`. Login requires a PTY: `false`. Platform quirks: .

## Command surface

Use `preflight`, `start`, `send`, `wait`, `observe`, `capture`, `permit`, `cancel`, and `stop` with the same platform/session/repository identity. `key escape` maps to cancellation; other native keys and editor replacement are PTY-only capabilities. `permit` / `cancel` / `stop` settle each permission `request_id` at most once; a second settler is `unknown-request`.

Humans watch with Terminal or host-wide `list` and session `view`. Orchestrator ordinary turns must not poll raw frames as a human UI. PTY remains login and native TUI takeover.

## Level-zero receipt

Every receipt identifies `schema_version`, `platform`, `session`, `repo`, `transport`, and Git facts. Mutation receipts also report `mutation_status`, outcome, stop reason, and available protocol events or final text.

`capture` defaults to compact final text. `--tools` includes tool events, `--since EVENT_OFFSET` selects newer events, `--full` includes the complete event record, and `--inline` returns content inline when supported.

`mutation_status` is one of `not_started`, `accepted`, `in_progress`, `completed`, or `unknown`. These are transport facts, not permission to retry.
