# ZCode ACP transport

Command: `python3 $SKILL_DIR/scripts/kaola-zcode-acp.py`. Login: see SKILL.md §Transport. Platform quirks: Runner-owned ACP translator over the installed ZCode app-server --stdio (Gate 2); william0wang/zcode-acp is a protocol reference only, never vendored and never npm; cli=0.16.9 is a record, not a live ACP run: check the actual CLI version before the next live run; explicit KAOLA_ZCODE_ENTRY and KAOLA_ZCODE_NODE, never PATH; child env allowlist with no auth injection; the enabled Coding Plan provider is registered in memory per backend process (mechanics in platform.md); agentInfo._meta.zcode reports providerId, baseURL, plan-cache status and model ids; both presets pin GLM-5.3 at thought=max, the pair the Issue #108 Host gate enforces (ZCODE_HOST_MODEL_ID/ZCODE_HOST_EFFORT in kaola-acp.py, test-asserted equal to this manifest); the live ACP model value is provider-qualified with a backslash (builtin:bigmodel-coding-plan\GLM-5.3, account:*\GLM-5.3 once the plan is registered) and comparison uses the tail after \ or /, so GLM-5.3-Flash never matches; the live effort config id is thoughtLevel while this manifest declares thought, and both the Runner read path and the adapter write path accept either alongside thought_level; neither model nor thoughtLevel advertises a currentValue at session/new, so a selection is verified only after it is applied.

## Command surface

Use `preflight`, `start`, `send`, `steer`, `wait`, `observe`, `capture`, `permit`, `cancel`, `stop`, and `drain-restart` with the same platform/session/repository identity. `drain-restart` needs `--resume ID` or `--continue`. It runs start's pre-spawn refusals first, then waits until the seat is idle, exact-stops, and starts again, carrying the recorded `--model`/`--effort`/`--tier`/`--fast` unless this command passes them. It is not a rebind. `status` reports `runner_build` (the holder file), `accepted_revision`, `stale` (holder, bridge, adapter, or platform manifest changed), and `reported_drift` (pin, CLI-file, or quota-catalog drift, a recorded script path that no longer exists, or an install tree that moved or was re-rooted, none of which blocks). A direct checkout start is `baseline_exempt` and does not block; a `~/.local/bin` start is not. `send` and `steer` refuse `seat-stale` unless `--confirm-stale` is passed. `stop` and `status` are not gated. `key escape` maps to cancellation; there are no other native keys and no editor replacement. `permit` / `cancel` / `stop` settle each permission `request_id` at most once; a second settler is `unknown-request`.

Humans watch with Terminal or host-wide `list`, session `view`, and local `follow`. Host-wide, read-only: `"$SKILL_DIR/scripts/kaola-acp.py" survey|list|packages|model-package` (`survey` reads installed CLIs from the login PATH and starts nothing; model rows add `quotaPool`). Orchestrator ordinary turns must not poll raw frames as a human UI.

## Level-zero receipt

Every receipt identifies `schema_version`, `platform`, `session`, `repo`, `transport`, and Git facts. Mutation receipts also report `mutation_status` (see SKILL.md; transport facts, not permission to retry), outcome, stop reason, and available protocol events or final text.

`capture` defaults to compact final text. `--tools` includes tool events, `--since EVENT_OFFSET` selects newer events, `--full` includes the complete event record, and `--inline` returns content inline when supported. Every ordinary `capture` receipt (`--lines`, `--since`, `--tools`) is bounded: over budget, the oldest entries are dropped and `truncated` records kept/dropped/total counts, the byte size and sha256 of the untruncated stream, and the `--full` hint; `--full` is the explicit, unbounded request. Ordinary `observe`/`status` receipts are bounded the same way on their own larger `state_receipt_bytes` budget (256 KiB): scalar facts stay whole, and an over-budget structure (`record`, `session_meta`, `initial_config_options`, `capabilities`, `agent_info`; `pending_permissions` keeps its newest entries) is replaced by its byte size and sha256 under `truncated.fields`.

## Steering (`steer`)

This platform's ACP steering facts, both modes, the receipt vocabulary and the races: [steering.md](steering.md).

## Model selection receipts

`start` applies the resolved selection through the agent's advertised `session/set_config_option`
IDs — model, then effort, then Fast (`model`/`thought`).
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
