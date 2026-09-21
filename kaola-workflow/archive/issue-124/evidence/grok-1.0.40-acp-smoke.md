# #124 live ACP smoke — grok 1.0.40 (2026-09-21)

Candidate: branch workflow/issue-124 @ 14a329f, scripts run from the worktree (`scripts/kaola-acp.py grok ...`).
Binary: `/opt/homebrew/bin/grok` -> `@xai-official/grok/bin/grok-native`, `grok --version` = `grok 1.0.40 (eb1a2256660d)`.
Scratch repo `/tmp/kpr-i124-smoke/repo`, isolated `KAOLA_ACP_RECORD_ROOT=/tmp/kpr-i124-smoke/records`,
session `grok-kaola-i124-smoke`; inherited `KAOLA_*` Host vars removed with `env -u`; network via
command-prefix `HTTPS_PROXY`/`HTTP_PROXY` only (session-scoped; no persistent proxy/config file touched).
Raw files: `grok-1.0.40-acp-smoke/`.

| step | command | rc | fact |
|---|---|---|---|
| start | `start` | 0 | `state: ready`, `acp_session_id 01a0c474-c92d-7141-9e70-22e9a7233da7`, `protocol_version 1`, `agent_info {}`; `transport.cli_version = {path: /opt/homebrew/bin/grok, version: "grok 1.0.40 (eb1a2256660d)", verified_versions: "cli=1.0.25;protocol=1"}` — started although the version differs from verified (acceptance 1) |
| send | `send --wait` "Reply with exactly the single word PONG" | 0 | `outcome turn_completed`, `stop_reason end_turn`, `final_text PONG` |
| read | `observe` | 0 | `state ready`, `activity_hint idle`, `turn_outcome turn_completed` |
| cancel | `send --no-wait` (3000-word essay) then `cancel` ~8 s later | 0/0 | `outcome turn_canceled`, `stop_reason cancelled` |
| stop | `stop` | 0 | `agent_exit_code 0`, `residual_pids []`; holder/agent pids 63398/63399 gone (`ps` empty) |

`events.jsonl` (acceptance 2): `turn_ended outcome=turn_completed stop_reason=end_turn` (cursor 71),
`turn_ended outcome=turn_canceled stop_reason=cancelled` (cursor 80), `process_exited code 0 signal null` (cursor 84).
`record.json`: `cli_version` as above, `state stopped`, `agent_alive false`.

Contract re-check vs the manifest and the #65 steering record:
- `initialize`: protocolVersion 1; no `agentInfo` (the version is in `result._meta.agentVersion = "1.0.40"`, a non-standard field the Runner does not read);
  capabilities `loadSession`, `sessionCapabilities {list, resume, close}`, `_meta` keys `x.ai/fs_notify`, `x.ai/hooks`, `x.ai/capabilities` — no steering `_meta`
  (`steer-probe-grok-1.0.40.json`, the archived #65 `steer_probe.py`, idle phase only, no model spend).
- `session/new`: `configOptions` ids `model` (grok-4.6) and `reasoning_effort` (xhigh) — matches `acp_model_config_id`/`acp_effort_config_id`; the Runner applied both (4 `config_options_applied` events).
- `session/prompt` stopReason: `end_turn` and `cancelled`, both mapped normally.
- `_x.ai/*` extension notifications seen: session/setup, session_notification, sessions/changed, queue/changed, announcements/update, mcp/server_status, mcp/init_progress, models/update, settings/update, session/prompt_complete, mcp/servers_updated, mcp_initialized — all recorded as `notification` events, none broke the holder (0 malformed lines, 0 handler errors).
- Steering: `_session/steering` and `_session/steer` -> -32601 `data: "unknown ACP extension method: session/steering|steer"`; `session/steering`, `session/steer` -> -32601. Unchanged from 1.0.25/1.0.34.
- exit: `process_exited code 0` after stop.
- stderr: one line at stop, `Failed to spawn MCP server 'context7': session is closing` — the user's own MCP config, spawned during shutdown; not a contract fact.
