# Devin CLI ACP transport

Command: `devin acp`. Login: see SKILL.md §Transport. Platform quirks: agent reports affogato 0.0.0-dev; the ACP model option offers only 76 of the catalog values on cli 3000.11.1 and rejects the presets with -32602, so each tier sets its preset through acp_command_<tier> spawn argv --model (Issue #140); the advertised model option does not echo, and need not list, that argv id, so its currentValue is not the running model (Issue #197: a default seat advertised swe-2-high while Devin's native sessions.db recorded swe-2-max, and an opus-fusion seat advertised the -high fusion id), and the Runner reads no native store, so the actual model stays unknown; both non-default tiers are fusion models (Issue #144): --tier opus-fusion is fusion-claude-opus-5-5-high-sidekick-swe-2-medium (main Opus effort high, SWE-2 sidekick medium; Issue #190 and Issue #197 recorded the earlier preset fusion-claude-opus-5-5-medium-sidekick-swe-2-medium, main Opus effort medium, and Devin's native sessions.db recorded that -medium id for an opus-fusion session; the #144-measured id was the -high variant), and --tier fable is fusion-claude-fable-5-1-high-sidekick-swe-2-medium, replacing the retired pure claude-fable-5-1-high; there is no effort config option, so every effort is encoded in the model id.

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
IDs — model, then effort, then Fast (`model`).
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

Droid `PreCompact` and Cursor `preCompact` can call `scripts/kaola-project-compact-notice.py`
with an exact owned binding. This KPR local socket operation keeps completion unconfirmed and
uses the same holder's standard prompt after the targeted request ends successfully. No hook is
installed automatically. Native policy/trust and current Codex automatic recovery stay unchanged.
Full installed Skill reads and task continuation need actual tool/output evidence. See the
checkout's `docs/api.md`, “Opt-in Droid/Cursor project precompact notice”, for binding fields,
verified config roots, failed/unknown admission and old-holder recovery. Do not use a Stop hook
as completed-compaction proof or replay an unknown write.
