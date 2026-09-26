# Claude Code ACP transport

Command: `node $SKILL_DIR/scripts/vendor/claude-code-acp/dist/index.js`. Login: see SKILL.md §Transport. Platform quirks: vendored pinned fork of harukitosa/claude-code-acp (MIT), never npm or npx; one claude -p subprocess per turn, driven with --input-format stream-json over an open stdin (later turns add --resume) - the same channel that carries native mid-turn steering behind _session/steering; the bridge drops ANTHROPIC_API_KEY/ANTHROPIC_AUTH_TOKEN so the subscription login and native Settings resolve inside claude; permit settles only the reported tool_call status because the child takes no --permission-prompt-tool, so a permission answer cannot gate or resume it (cli 2.1.272 emitted no permission_request); a fresh seat's recorded acp_session_id is process-local and can never be resumed after a stop - --resume needs the native Claude UUID from the newest native_session_identity session update (readable with capture), which the bridge emits on a seat's first turn (fresh, resumed, or cancelled) and again after a resume-failure fallback, exactly once per native id, preferring the announced id on a cancelled fallback turn, and never clearing a binding for an empty id (Issue #186).

## Command surface

Use `preflight`, `start`, `send`, `steer`, `wait`, `observe`, `capture`, `permit`, `cancel`, `stop`, and `drain-restart` with the same platform/session/repository identity. `drain-restart` needs `--resume ID` or `--continue`. It runs start's pre-spawn refusals first, refuses `drain-not-idle` immediately when the seat is busy (leaving it up; retry timing is the Agent's), otherwise one idle exact-stop, and starts again carrying the recorded `--model`/`--effort`/`--tier`/`--fast` unless this command passes them. There is no idle polling and no scan of other seats: adoption is the new start's own `dispatcher`. It is not a rebind. `status` reports `runner_build` (the holder file), `accepted_revision`, `stale` (holder, bridge, quota catalog, adapter, or platform manifest changed), and `reported_drift` (the report-only drift codes; see that field, and neither it nor `stale` blocks). A direct checkout start is `baseline_exempt` and does not block; a `~/.local/bin` start is not. `key escape` maps to cancellation; there are no other native keys and no editor replacement. `permit` / `cancel` / `stop` settle each permission `request_id` at most once; a second settler is `unknown-request`.

Humans watch with Terminal or host-wide `list`, session `view`, and local `follow`. Host-wide, read-only: `"$SKILL_DIR/scripts/kaola-acp.py" survey|list|packages|model-package` (`survey` reads installed CLIs from the login PATH and starts nothing; model rows add `quotaPool`). Orchestrator ordinary turns must not poll raw frames as a human UI.

## Level-zero receipt

Every receipt identifies `schema_version`, `platform`, `session`, `repo`, `transport`, and Git facts. Mutation receipts also report `mutation_status` (see SKILL.md; transport facts, not permission to retry), outcome, stop reason, and available protocol events or final text.

`capture` defaults to compact final text. `--tools` includes tool events, `--since EVENT_OFFSET` selects newer events, `--full` includes the complete event record, and `--inline` returns content inline when supported. Every ordinary `capture` receipt (`--lines`, `--since`, `--tools`) is bounded: over budget, the oldest entries are dropped and `truncated` records kept/dropped/total counts, the byte size and sha256 of the untruncated stream, and the `--full` hint; `--full` is the explicit, unbounded request. Ordinary `observe`/`status` receipts are bounded the same way on their own larger `state_receipt_bytes` budget (256 KiB): scalar facts stay whole, and an over-budget structure (`record`, `session_meta`, `initial_config_options`, `capabilities`, `agent_info`; `pending_permissions` keeps its newest entries) is replaced by its byte size and sha256 under `truncated.fields`.

## Steering (`steer`)

This platform's ACP steering facts, both modes, the receipt vocabulary and the races: [steering.md](steering.md).

## Model selection receipts

`start` applies the resolved selection through the agent's advertised `session/set_config_option`
IDs — model, then effort, then Fast (`model`/`effort`/`fast`).
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
