# Antigravity ACP transport

Command: `python3 $SKILL_DIR/scripts/kaola-antigravity-acp.py`. Login: see SKILL.md §Transport. Platform quirks: in-repo adapter over agy's headless stream-json protocol (no official ACP, no third-party bridge); one agy child per ACP session, started at session/new so an unsigned account refuses there, and replaced before the next prompt when model or mode changed; sessionCapabilities is {resume,close}, resume is agy --conversation <conversation_id> carried by session/resume, and native_session_identity announces the native id; session/list, session/load and Runner --continue are unsupported by this ACP route (native agy separately advertises --continue); model and mode are the only config options, effort is part of the model id and the adapter never passes --effort; tested stream-json control_request and CLI-local /usage end agy with ERROR, finished_reason=error and exit 2; mid-turn stdin user events run after the active turn on the same process and are coalesced behind _session/steering, whose written/write-only result proves admission rather than consumption and whose idle result is promptRequired; live SIGINT returns ERROR/interrupted with finished_reason=interrupted and exit 1 while retaining the on-disk conversation, so cancel settles as cancelled and the next prompt respawns with --conversation; finished_reason=print_timeout or error is incomplete even when status is SUCCESS, and interrupted settles as cancelled including when a steer is queued; metadata retains finished_reason and incomplete partial_response; one-shot agy -p /usage --output-format json reports 0 turns and 0 tokens with command.data.groups containing two groups and four buckets (gemini-weekly, gemini-5h, 3p-weekly, 3p-5h), remaining_fraction in [0,1] and RFC3339 reset_time; each result._meta.antigravity.usage carries native conversation-cumulative usage rather than a per-turn delta; the adapter itself does not write ~/.gemini, but the native CLI may persist its own data; one-turn, two-turn, model/mode replacement, close/resume, mid-turn steer, cancel/interrupt+resume and quota were verified live on agy 1.4.12 on 2026-10-31, with final-candidate direct/launchd six-key proxy isolation and focused finished_reason verification; the initial native id is provisional when first-prompt model/mode application replaces the child, so use the last native_session_identity for resume.

## Command surface

Use `preflight`, `start`, `send`, `steer`, `wait`, `observe`, `capture`, `permit`, `cancel`, `stop`, and `drain-restart` with the same platform/session/repository identity. `start --text` or `start --stdin` is the first `session/prompt`: a dispatch only with `brief_delivered` true, `turn_request_id`, and that turn's `prompt_fingerprint`. `--no-wait` checks admission, not turn end. Neither flag: seat-only (`ready`, no turn). `drain-restart` needs `--resume ID` or `--continue`. It runs start's pre-spawn refusals first, refuses `drain-not-idle` immediately when the seat is busy (leaving it up; retry timing is the Agent's), otherwise one idle exact-stop, and starts again carrying the recorded `--model`/`--effort`/`--tier`/`--fast` unless this command passes them. There is no idle polling and no scan of other seats: adoption is the new start's own `dispatcher`. It is not a rebind. `rebind-host`, run only from inside the live replacement Host, moves an existing seat's carrier to that Host in place; the seat keeps its holder, agent and native session. `status` reports `runner_build` (the holder file), `accepted_revision`, `stale` (holder, bridge, quota catalog, adapter, or platform manifest changed), and `reported_drift` (the report-only drift codes; see that field, and neither it nor `stale` blocks). A direct checkout start is `baseline_exempt` and does not block; a `~/.local/bin` start is not. `key escape` maps to cancellation; there are no other native keys and no editor replacement. `permit` / `cancel` / `stop` settle each permission `request_id` at most once; a second settler is `unknown-request`.

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
