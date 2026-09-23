# ZCode ACP transport

Command: `python3 $SKILL_DIR/scripts/kaola-zcode-acp.py`. Login is a human act in a native terminal, outside the Runner (needs a terminal: `false`). Platform quirks: Runner-owned ACP translator over the installed ZCode app-server --stdio (Gate 2); william0wang/zcode-acp is a protocol reference only (Apache-2.0 pin 80aa4e2), never vendored and never npm; cli=0.16.9 (ZCode.app 3.14.1) and upstream v0.46.6 (turnId, permissions) are harness-compat 2026-09-22 records, not a live ACP run; check the actual CLI version before the next live run; explicit KAOLA_ZCODE_ENTRY and KAOLA_ZCODE_NODE, never PATH; child env allowlist with no auth injection; the enabled Coding Plan provider is registered in memory per backend process -- on ZCode 3.12+ via provider/updateAccountConfig plus session/setModel on the account:* provider with the credential supplied only through interaction/requestProviderRuntimeHeaders, and on pre-3.12 app-servers via the runtimeModel overlay on session/create, session/resume and session/setModel (launch facts in platform.md); agentInfo._meta.zcode reports providerId, baseURL, plan-cache status and model ids; the Runner default and upgrade presets both pin GLM-5.3 at thought=max, the same pair the Issue #108 Host gate enforces (ZCODE_HOST_MODEL_ID/ZCODE_HOST_EFFORT in kaola-acp.py; their equality with this manifest is asserted by a test, so there is no second source of truth); the bare id is what this manifest declares because the live ACP option value is provider-qualified with a backslash (builtin:bigmodel-coding-plan\GLM-5.3 on the builtin plan, account:*\GLM-5.3 once the plan is registered) and comparison uses the tail after \ or /, so GLM-5.3-Flash never matches; the live effort config id is thoughtLevel while this manifest declares thought, which both the Runner read path and the adapter write path accept alongside thought_level; neither model nor thoughtLevel advertises a currentValue at session/new, so a selection is verified only after it is applied; login happens in the ZCode desktop App; the bundled runtime ships no terminal UI.

## Command surface

Use `preflight`, `start`, `send`, `steer`, `wait`, `observe`, `capture`, `permit`, `cancel`, and `stop` with the same platform/session/repository identity. `key escape` maps to cancellation; there are no other native keys and no editor replacement. `permit` / `cancel` / `stop` settle each permission `request_id` at most once; a second settler is `unknown-request`.

Humans watch with Terminal or host-wide `list`, session `view`, and local `follow`. Installed CLIs are the host-wide, read-only `kaola-acp survey` (login PATH; starts nothing). Orchestrator ordinary turns must not poll raw frames as a human UI. ACP is the only transport; a request for PTY is refused with `transport-pty-retired`.
Read-only `packages`/`model-package`; model rows add `quotaPool`.

## Level-zero receipt

Every receipt identifies `schema_version`, `platform`, `session`, `repo`, `transport`, and Git facts. Mutation receipts also report `mutation_status`, outcome, stop reason, and available protocol events or final text.

`capture` defaults to compact final text. `--tools` includes tool events, `--since EVENT_OFFSET` selects newer events, `--full` includes the complete event record, and `--inline` returns content inline when supported. Every ordinary `capture` receipt (`--lines`, `--since`, `--tools`) is bounded: over budget, the oldest entries are dropped and `truncated` records kept/dropped/total counts, the byte size and sha256 of the untruncated stream, and the `--full` hint; `--full` is the explicit, unbounded request. Ordinary `observe`/`status` receipts are bounded the same way on their own larger `state_receipt_bytes` budget (256 KiB, Issue #64, so a realistic `session_meta` and the stored `record` stay whole and `configOptions` `currentValue` — the configured model — remains readable): scalar facts stay whole, and an over-budget structure (`record`, `session_meta`, `initial_config_options`, `capabilities`, `agent_info`; `pending_permissions` keeps its newest entries) is replaced by its byte size and sha256 under `truncated.fields`.

`mutation_status` is one of `not_started`, `accepted`, `in_progress`, `completed`, or `unknown`. These are transport facts, not permission to retry.

## Steering (`steer`)

This platform's ACP steering facts, both modes, the receipt vocabulary and the races: [steering.md](steering.md).

`start` resolves the tier/model/effort/Fast selection through the shared model policy and applies it through the
agent's advertised `session/set_config_option` IDs — model first, then effort, then Fast — using
`model`/`thought`/`` when non-empty.
An effort id may list `;`-separated candidates in order; the first one the agent advertises after
the model apply is used (`config_application.effort.candidates`/`advertised`,
`effective_selection.effort_config_id`), otherwise the first literally.
`start` and `preflight` wait for the `session/new` answer up to the manifest's
`acp_session_new_timeout` seconds (15 when absent); no answer by then is `acp-session-timeout`.
A manifest may declare `acp_init_meta` (`key=value` pairs sent as `clientCapabilities._meta`
during `initialize`): agents that negotiate a parameterized model picker advertise separate
`model`/`effort`/`fast` options with base model IDs and string `true`/`false` fast values instead
of fixed variant descriptors. A manifest may declare `acp_command_default`/`_upgrade`/`_alt`: the
tier preset then spawns that command unless `--command`, `KAOLA_ACP_COMMAND`, `--model` or a preserved
resume applies; a model the spawn argv carries as `--model` is not re-sent as an option
(`config_application.model.applied_via: argv`, `effective_selection.effective_model_source: launch-argv`
beside the agent's `advertised_model`). When a manifest declares `acp_model_map`, a resolved catalog model ID decomposes onto
the ACP model value the agent advertises for the same model — effort encoded in the picker ID
suffix then travels through the effort option and Fast through the fast option (values converted
per `acp_fast_values`), recorded as `requested_id`/`mapped`/`declared` in the model application.
Model semantics are never substituted: an unmapped ID is sent literally and its rejection is
reported as a limitation. `config_application` records each attempted option's requested value and
applied result; `configured_options` carries the adapter's returned receipts. An option with no
advertised config ID, or one the adapter rejects, is reported as a limitation — the session stays
usable. The `fast` receipt's `effective` reflects proven native state only: a rejected fast option
or an unapplied fast-variant model ID reports `unknown`, and an applied model value's own
descriptor (e.g. `[..,fast=true]`) is reported as the effective fast evidence with any request
conflict noted — never a false on/off.

## Ending and resuming an ACP session

A turn reaching `end_turn` is a reply boundary, not task completion; the Agent judges from the
result whether work continues. When the Agent chooses `stop`, the Runner sends `session/close`
when the adapter advertises that capability, then exits the exactly-owned holder and agent
processes and reports actual exit plus any residue. `stop` does not call `session/delete`,
wipe CLI-side history, or imply the adapter persisted anything — a platform's resume and
history behavior stands on its own verified capability, not on the close call's name. If
in-flight work exists when the Agent has already chosen to stop, the existing `cancel`/exit
path applies.

To resume later work, the Agent chooses `start --resume <session-id>` (the Runner uses
`session/resume` or `session/load` per the advertised capability) or `start --continue`,
which selects the latest `session/list` entry for the repository's canonical cwd. Neither is
guaranteed by the protocol universally; when a platform cannot resume or history is
unavailable, the Agent starts a fresh session and continues from existing work records. The
Runner never auto-resumes, retries an old prompt, or continues a Workflow on its own.
