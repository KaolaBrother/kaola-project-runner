# dsh ACP transport

Command: `dsh --profile acp`. Login: see SKILL.md §Transport. Platform quirks: native server (no bridge, acp_wrapper_pin empty); agentInfo is deepseek-harness-acp/0.0.1 under launcher dsh 0.1.5-rc.2; sessionCapabilities is {close,list,resume}, so the Runner takes the session/resume branch, whose result carries configOptions but no sessionId; session/load, session/set_mode, session/delete, session/fork and terminal/* answer -32601, so there is no mode config option; config options arrive in the session/new result: model (JSON-encoded [provider,model] strings, mapped from plain ids by acp_model_map) and reasoning_effort (off/low/high/max, route-dependent); session/list entries carry only sessionId and cwd (no updatedAt), so --continue is unsupported; the shipped acp profile pins provider deepseek-official regardless of the user's agent-default-model, so a ready session may still fail its first prompt with no API key for provider route "deepseek-official" unless DEEPSEEK_API_KEY is set or --model selects a credentialed route; the ACP composition sends no session/request_permission at all; the permission mode is the launch variable DSH_PERMISSION_MODE (Runner default danger-full-access, see SKILL.md), and dsh's own default workspace-write denies shell writes outside the workspace, /tmp and $TMPDIR and is inherited by any Runner start from that shell; creating an acp profile with --from-default-profile writes under $DSH_HOME and is an operator precondition the Runner never performs.

## Command surface

Use `preflight`, `start`, `send`, `steer`, `wait`, `observe`, `capture`, `permit`, `cancel`, and `stop` with the same platform/session/repository identity. `key escape` maps to cancellation; there are no other native keys and no editor replacement. `permit` / `cancel` / `stop` settle each permission `request_id` at most once; a second settler is `unknown-request`.

Humans watch with Terminal or host-wide `list`, session `view`, and local `follow`. Host-wide, read-only: `"$SKILL_DIR/scripts/kaola-acp.py" survey|list|packages|model-package` (`survey` reads installed CLIs from the login PATH and starts nothing; model rows add `quotaPool`). Orchestrator ordinary turns must not poll raw frames as a human UI.

## Level-zero receipt

Every receipt identifies `schema_version`, `platform`, `session`, `repo`, `transport`, and Git facts. Mutation receipts also report `mutation_status` (see SKILL.md; transport facts, not permission to retry), outcome, stop reason, and available protocol events or final text.

`capture` defaults to compact final text. `--tools` includes tool events, `--since EVENT_OFFSET` selects newer events, `--full` includes the complete event record, and `--inline` returns content inline when supported. Every ordinary `capture` receipt (`--lines`, `--since`, `--tools`) is bounded: over budget, the oldest entries are dropped and `truncated` records kept/dropped/total counts, the byte size and sha256 of the untruncated stream, and the `--full` hint; `--full` is the explicit, unbounded request. Ordinary `observe`/`status` receipts are bounded the same way on their own larger `state_receipt_bytes` budget (256 KiB): scalar facts stay whole, and an over-budget structure (`record`, `session_meta`, `initial_config_options`, `capabilities`, `agent_info`; `pending_permissions` keeps its newest entries) is replaced by its byte size and sha256 under `truncated.fields`.

## Steering (`steer`)

This platform's ACP steering facts, both modes, the receipt vocabulary and the races: [steering.md](steering.md).

## Model selection receipts

`start` applies the resolved selection through the agent's advertised `session/set_config_option`
IDs — model, then effort, then Fast (`model`/`reasoning_effort`).
Read `config_application` (each option's requested value and applied result), `effective_selection`
(what the agent then reports), `configured_options` (the adapter's returned receipts), and
`fast.effective` (proven native state only, otherwise `unknown`). An unapplied option — no
advertised config ID, or rejected by the adapter — is a reported limitation: the session stays
usable and no other model is substituted. `start` and `preflight` wait for the `session/new` answer
up to the manifest's `acp_session_new_timeout` seconds (15 when absent); no answer by then is
`acp-session-timeout`.

## Ending and resuming an ACP session

`stop` sends `session/close` when the adapter advertises it, then exits the exactly-owned holder and
agent processes and reports actual exit plus any residue; it never calls `session/delete` or wipes
CLI-side history. `start --resume <session-id>` uses `session/resume` or `session/load` per the
advertised capability; `start --continue` selects the latest `session/list` entry for the
repository's canonical cwd. Neither is universal: where resume is unavailable, the Agent starts a
fresh session from existing work records.
