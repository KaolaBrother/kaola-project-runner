# ACP live verification — 2026-09-11

## Environment

All receipts used protocol version 1 and schema version 3 on macOS. Evidence summaries are under `kaola-workflow/bundle-18-19-20-21/evidence/`.

## Cursor CLI

- CLI `2026.09.10-fd3934a`; initialize PASS; login not required; `agentInfo` empty.
- `configOptions`: `mode`, `model`; effort is encoded in model values.
- Scenario 1 PASS: `ACP_OK`, `end_turn`, no tools or changed files.
- Scenario 3 PASS: `prompt_timeout`, cancel, `turn_canceled` / `cancelled`.
- Scenario 4 PASS: stop returned `residual_pids: []`.
- Scenario 7 PASS: missing executable returned `acp-spawn-failed`; explicit PTY start/send/stop then succeeded.

## Devin CLI

- CLI `3000.10.21`; agent `affogato 0.0.0-dev`; initialize PASS; login not required.
- `configOptions`: `mode`, `model`; no separate effort option.
- Scenarios 1, 3, 4, and 7 PASS with the same outcomes as Cursor.
- The first PTY launch exposed an oversized model-catalog receipt. Compacting catalog evidence to count plus candidate membership fixed the command-length failure; the repeated PTY round trip passed.

## OpenCode

- CLI/agent `1.18.29`; initialize PASS; login not required.
- `configOptions`: `model`, `effort`, `mode`.
- Scenarios 1, 3, 4, and 7 PASS with the same outcomes as Cursor.

## Claude Code wrapper

- Wrapper pin `0.18.0` fetched and launched, then exited before initialize with `acp-initialize-failed` / `probe-eof`.
- Protocol, agent information, and login state were therefore unavailable. The manifest remains PTY-default and records that login requires a PTY.

## Kimi permission probe

- CLI/agent `0.41.0`, protocol 1.
- Default mode file-writing prompt completed with no `session/request_permission`.
- `mode=plan` was applied through `session/set_config_option`; the file-writing prompt produced request `0`, title `ExitPlanMode`, with `plan_approve`, `plan_revise`, and `plan_reject_and_exit` options.
- `permit --request-id 0 --option plan_approve` succeeded; the turn completed with `end_turn`; stop returned `residual_pids: []`.
