# Issue #445 live path (installed grok 1.0.70)

Probe date 2026-11-01. Binary `grok 1.0.70 (f50904eaee6c)` at
`~/.local/node-v24.14.0-darwin-arm64/bin/grok`, unchanged PATH.
Scratch repo `/tmp/kpr-445-smoke`. Record root `/tmp/kpr-445-records`.
Session `grok-kaola-i445-acp70`. Command path: worktree
`scripts/kaola-tmux.sh grok … --launch-backend direct --tier default`.
Inherited host and dispatcher variables were unset for this probe only,
so the seat was standalone (`heartbeat_host` null). No install and no
account change.

## Receipts

| step | file | result |
|---|---|---|
| preflight (skill script) | `01-preflight.json` | `ready`, transport `acp`, `protocol_version` 1, runtime `1.0.70`, `login_required` false |
| skill-mediated start | `02-start.json` | `refused`, `worker-skill-build-skew`, `mutation_status` `not_started`. Installed Skill copies differ from this checkout. Nothing spawned. |
| checkout start with inherited host binding | `03-start.json` | `refused`, `heartbeat-host-conflict`, `mutation_status` `not_started`. Nothing spawned. |
| checkout start | `04-start.json` | `state` `ready`, `baseline_exempt` true, `launch_backend` `direct`, `protocol_version` 1, cli `grok 1.0.70 (f50904eaee6c)`, model `grok-4.7` applied, `reasoning_effort` `high` applied, fast not advertised, `session_role` `elite` (preset class) |
| observe | `05-observe.json` | `state` `ready`, `agent_alive` true, `turn_active` false, `protocol_version` 1, `fatal_error` null, `agent_message_errors` 0 |
| send | `06-send.json` | `outcome` `turn_completed`, `stop_reason` `end_turn`, `mutation_status` `completed`, `final_text` `PONG-445`, `tool_calls.count` 0, `side_effects` commands 0 and files 0, `duration_ms` 3049 |
| capture | `07-capture.json` | transport `acp`, level L2, events kept 47 / dropped 14, stream sha256 `a8c569d59376fbe0f4872e134d479cfd847c16e6fdedca776145e3276a5ede53`. Five kept events contain `PONG-445`. |
| stop | `08-stop.json` | `stopped` true, `agent_exit_code` 0, `residual_pids` `[]`, `mutation_status` `completed` |
| status | `09-status.json` | `state` `stopped`, `outcome` `stopped`, `stale` false, `residual_pids` `[]` |

Holder pid 57024 and agent pid 57034 were both dead after stop.
Scratch `README.md` stayed unmodified. The runner left
`.kaola/host-registry.lock` in the scratch repo.

## Not remeasured

Steer (`_x.ai/interject`) was not sent. Both the 1.0.40 and 1.0.70
binaries contain the contiguous string `x.ai/interject` and do not
contain `_x.ai/interject`. The manifest steering summary still cites
CLI 1.0.46. That sentence is unchanged.

## Verdict

GREEN for the required path on installed 1.0.70: protocol negotiated at
1, the native command and config ids behaved as on the R manifest, and
exact stop left no residual pid. The pin may move from `cli=1.0.40` to
`cli=1.0.70` with `protocol=1`. No quirk change.
