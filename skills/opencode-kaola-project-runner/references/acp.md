# OpenCode ACP transport

Command: `python3 $SKILL_DIR/scripts/kaola-opencode-acp.py`. Login: see SKILL.md §Transport. Platform quirks: no ACP skip-all config option: model/effort/mode are ACP selections, not launch-level permission policy; requests offer allow_once/allow_always/reject_once. OpenCode V2 2.0.22/protocol 1 consumed the native OPENCODE_CONFIG file slot in actual ACP QA. Runner selects agents.build.permissions allow only when no existing config source or explicit mode/resume/custom command exists; this avoids overriding global or project policy, and never merges supplied OPENCODE_CONFIG or OPENCODE_CONFIG_CONTENT. plan and session permissions remain native; permit settles each request that still arises. V1 permission/bash/task schema is distinct from V2 permissions/shell/subagent; V2.0.11-to-2.0.22 source comparison does not establish a version-drift cause. V2 reaches its own server over loopback HTTP, and a forward proxy on that hop leaves initialize working while every session method answers ClientError; so when HTTP(S)_PROXY is set, the Runner appends any missing 127.0.0.1/localhost to NO_PROXY/no_proxy in the opencode child env only, keeping operator entries and never touching the Runner env. OpenCode 2.0.22 publishes later providers after session/new: the first model list can be only opencode/ while a following config_option_update adds opencode-go/deepseek-v4.1-flash. Setting that id before the update returns JSON-RPC -32602 model not found; start waits, bounded, until the live option list advertises the requested id and then sets it, with no model substitution.

## Command surface

Use `preflight`, `start`, `send`, `steer`, `wait`, `observe`, `capture`, `permit`, `cancel`, `stop`, and `drain-restart` with the same platform/session/repository identity. `drain-restart` needs `--resume ID` or `--continue`. It runs start's pre-spawn refusals first, refuses `drain-not-idle` immediately when the seat is busy (leaving it up; retry timing is the Agent's), otherwise one idle exact-stop, and starts again carrying the recorded `--model`/`--effort`/`--tier`/`--fast` unless this command passes them. There is no idle polling and no scan of other seats: adoption is the new start's own `dispatcher`. It is not a rebind. `rebind-host`, run only from inside the live replacement Host, moves an existing seat's carrier to that Host in place; the seat keeps its holder, agent and native session. `status` reports `runner_build` (the holder file), `accepted_revision`, `stale` (holder, bridge, quota catalog, adapter, or platform manifest changed), and `reported_drift` (the report-only drift codes; see that field, and neither it nor `stale` blocks). A direct checkout start is `baseline_exempt` and does not block; a `~/.local/bin` start is not. `key escape` maps to cancellation; there are no other native keys and no editor replacement. `permit` / `cancel` / `stop` settle each permission `request_id` at most once; a second settler is `unknown-request`.

Humans watch with Terminal or host-wide `list`, session `view`, and local `follow`. Host-wide, read-only: `"$SKILL_DIR/scripts/kaola-acp.py" survey|list|packages|model-package` (`survey` reads installed CLIs from the login PATH and starts nothing; model rows add `quotaPool`). Orchestrator ordinary turns must not poll raw frames as a human UI.

## Level-zero receipt

Every receipt identifies `schema_version`, `platform`, `session`, `repo`, `transport`, and Git facts. Mutation receipts also report `mutation_status` (see SKILL.md; transport facts, not permission to retry), outcome, stop reason, and available protocol events or final text.

`capture` defaults to compact final text. `--tools` includes tool events, `--since EVENT_OFFSET` selects newer events, `--full` includes the complete event record, and `--inline` returns content inline when supported. Every ordinary `capture` receipt (`--lines`, `--since`, `--tools`) is bounded: over budget, the oldest entries are dropped and `truncated` records kept/dropped/total counts, the byte size and sha256 of the untruncated stream, and the `--full` hint; `--full` is the explicit, unbounded request. Ordinary `observe`/`status` receipts are bounded the same way on their own larger `state_receipt_bytes` budget (256 KiB): scalar facts stay whole, and an over-budget structure (`record`, `session_meta`, `initial_config_options`, `capabilities`, `agent_info`; `pending_permissions` keeps its newest entries) is replaced by its byte size and sha256 under `truncated.fields`.

## Steering (`steer`)

This platform's ACP steering facts, both modes, the receipt vocabulary and the races: [steering.md](steering.md).

## Model selection receipts

`start` applies the resolved selection through the agent's advertised `session/set_config_option`
IDs — model, then effort, then Fast (`model`/`effort`).
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

## Optional project precompact notice

An exact owned binding can call `scripts/kaola-project-compact-notice.py`. This
KPR local socket operation keeps completion unconfirmed and uses the same
holder's standard prompt after the targeted request ends successfully. No hook
is installed automatically. Native policy/trust and current Codex automatic
recovery stay unchanged. Full installed Skill reads and task continuation need
actual tool/output evidence. See the checkout's `docs/api.md` section for the
opt-in project precompact notice. That section has the binding fields, the
verified config roots, failed or unknown admission, and old-holder recovery.
Do not use a Stop hook as completed-compaction proof. Do not replay an unknown
write.
