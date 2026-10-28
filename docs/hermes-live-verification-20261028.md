# Hermes ACP live verification — 2026-10-28

MacBook leg of issue #417. The Mac Mini leg is deferred: the Mini was offline and SSH was denied. No Mac Mini receipt was taken and none was copied from this machine. Fields that need that machine stay unmeasured.

This run is transport measurement through the hermes Runner. It adds no `worker_grants` row. Hermes seat count stays 0. No release, tag, or ship (#418). `templates/grok-golden/` was not touched. KPR did not read or write `$HERMES_HOME` (including `~/.hermes/.env`) and did not run `--setup`, `--setup-browser`, or `--accept-hooks`.

Raw frames and receipts stayed on this machine under `/tmp/kpr-417-frames/wire.jsonl` and `/tmp/kpr-417-receipts/`. Record root: `KAOLA_ACP_RECORD_ROOT=/tmp/kpr-417-records`. Throwaway repo: `/tmp/kpr-417-smoke-repo` (resolved `/private/tmp/kpr-417-smoke-repo`, record dir `f4d54992690f0142`). The Runner was invoked from the issue-417 worktree with `HERMES_BIN` pointed at a stdio tee whose real binary was `~/.local/bin/hermes`, `--launch-backend direct`, and heartbeat/dispatcher variables unset.

## Version and identity

- CLI: `Hermes Agent v0.22.5 (2026.9.24) · stable · local bf0203a794a0` (`~/.local/bin/hermes`).
- `initialize` result: `protocolVersion` 1, `agentInfo` `hermes-agent` / `0.22.5`.
- Written `acp_verified_versions`: `cli=0.22.5;agent=hermes-agent/0.22.5;protocol=1;condition=macbook-20261028-mini-unmeasured`.
- Main session `--session`: `hermes-kaola-i417-macbook`.
- `acp_session_id`: `local-ecb75ab5174c39bd2421bc3b5155bf9b7af218ed55bc169f196cf0442efc31aa`.
- `_meta.hermes.sessionProvenance` at `compressionDepth` 0: `currentHermesSessionId` and `rootHermesSessionId` equal that ACP id, `parentHermesSessionId` null, `sessionKind` `root`.
- Holder during the smoke: pid 16489, `holder_instance_id` `dc9fc178c3c2ca4468bb345a474a3679`, adapter pid 16495. Launch argv on the live child was `hermes --yolo acp`. Child env had `HERMES_YOLO_MODE`, `HERMES_ACCEPT_HOOKS`, `HERMES_HOME`, and `HERMES_INFERENCE_PROVIDER` absent. No provider key was added to `acp_env_allowlist`.
- `name_role` / `session_role` reported `worker` from the `hermes-kaola-` session name. That is not a grant.

`initialize` from Hermes advertised `sessionCapabilities` `fork`, `list`, and `resume`. The adapter stripped `resume`. The start receipt's capabilities are `loadSession`, prompt image, and session `fork`/`list`. Auth methods on that initialize: `deepseek` ("deepseek runtime credentials", not a terminal method) and `hermes-setup` (terminal, args `--setup`).

## Smoke

Start (`/tmp/kpr-417-receipts/start.json`): `state` `ready`. Preset `hermes/default`, name `DeepSeek V4.1 Flash 1017`, resolved model `deepseek/deepseek-flash`, resolved effort `high`, source `runner-default`. Wire `session/set_model` `modelId` `deepseek:deepseek-flash` returned `{}`. Wire `session/set_mode` `modeId` `dont_ask` returned `{}`. Start receipt: model applied true, mapped true, value `deepseek:deepseek-flash`; mode applied true, value `dont_ask`; effort applied false, reason `no-advertised-config-option`, value `high`. `model_verified` stayed `unknown` (`actual-model-evidence-not-yet-read`) because the set result is empty. The adapter writes the requested value into `configOptions.currentValue`.

Observe and status while the holder was alive: `state` `ready`, `agent_alive` true, holder pid 16489, pending permissions empty. `session_meta.models.currentModelId` was still `auto:anthropic/claude-opus-4.6` and `session_meta.modes.currentModeId` was still `default` (the `session/new` snapshot). `configOptions` current values were `deepseek:deepseek-flash` and `dont_ask`. Those two views are not the same fact.

Send of one prompt (`Reply with exactly the single word pong...`): `stop_reason` `end_turn`, `outcome` `turn_completed`, `mutation_status` `completed`, `final_text` `pong`, `prompt_fingerprint` `sha256:c57e851c7f44452607d20069b796e8c456e1a8d154b59723b181ab02c4f92bae`. Wire prompt result id 5 usage: `cachedReadTokens` 3584, `inputTokens` 9432, `outputTokens` 3, `totalTokens` 13019. `context_usage` size 1048576, used 13019. The usage object has no model id.

`capture --lines 200`: level L2, 10 events, 3903 bytes. `capture --full`: 349 bytes, level L3, points at the event log (3642 bytes at that moment) and does not inline it.

## Model and provider read-back

`session/new` (wire frame, result id 2) before `set_model`:

- `currentModelId`: `auto:anthropic/claude-opus-4.6`
- catalog entry `deepseek:deepseek-flash`: name `DeepSeek · deepseek-flash`, description `Provider: DeepSeek`
- `currentModeId`: `default`
- available modes: `default`, `accept_edits`, `dont_ask`

`session/set_model` and `session/set_mode` results were `{}`.

A second viewer `session/load` of the live id (wire result keys `_meta`, `models`, `modes`; no top-level `sessionId`), before that viewer sent its own `set_mode`:

- `currentModelId`: `deepseek:deepseek-flash`
- description: `Provider: DeepSeek • current`
- `currentModeId`: `dont_ask`
- provenance ids unchanged, `compressionDepth` 0

Resume receipt (`resume-load.json`), started without `--tier`: model applied false, reason `no-resolved-value`, source `resume-preserved`; mode applied true, `dont_ask` (the holder re-applied mode); effort applied false, `no-resolved-value`; `effective_model` `deepseek:deepseek-flash` from the load snapshot. The second viewer was then exact-stopped. The primary stayed ready.

Slash prompt `/model` (evidence only, not a preset source): `stop_reason` `end_turn`, `final_text` `Current model: deepseek-flash` / `Provider: deepseek`. That agrees with the applied preset.

The model map stays `deepseek/deepseek-flash=deepseek:deepseek-flash`. The quota rule stays `provider_prefix` `deepseek`. The ACP surface has no base URL, so "DeepSeek official" here is the provider id `deepseek` plus the non-terminal auth method `deepseek runtime credentials`. An API host was not proven. The settled default was not changed.

## Mode, permission, cancel, steer

Permission probe on the main session, mode `dont_ask`, launch argv `--yolo`:

- `echo yolo-probe-ok` completed with no `session/request_permission` between the tool call and its update.
- A normal file edit completed with no permission request.
- `id_ed25519` produced two sequential `session/request_permission` requests (ids 0 and 1, tool call ids `edit-approval-1` and `edit-approval-2`). Options were `allow_once` and `deny`. Both were settled with `permit` `allow_once`. The turn then ended `end_turn` with pending 0.

So `dont_ask` reached the gateway session: a non-sensitive edit was auto-approved and a sensitive name still asked. Shell `echo` and later `sleep` also ran with pending 0. That is consistent with `--yolo` or with an allowlist. A command that is allowlisted even without `--yolo` was not run, so yolo's effect was not isolated. `--accept-hooks` was not passed and no TTY was attached. No unseen-hook prompt appeared. That does not prove hooks are disabled.

Cancel during `sleep 10`: the holder sent `session/cancel` (no id) for the main session id. Receipt: `stop_reason` `cancelled`, `outcome` `turn_canceled`, `mutation_status` `completed`.

Busy second prompt: the first `send --no-wait` of `sleep 12 && echo SLEPT` was `mutation_status` `in_progress`. The immediate second `send --no-wait` was refused before any wire write:

```json
{"code":"prompt-in-progress","message":"a prompt turn is already active; steer this turn (steer --delivery after-turn queues for the next turn) or retry send after turn_ended"}
```

The wire for that window has the sleep prompt only. The second prompt did not reach Hermes, was not queued there, and did not return `end_turn`. A bare after-turn `steer` (no `--steer-mode`) was refused `steer-mode-required`: hermes has no verified native mid-turn entry (`native_steering=unknown`); nothing was written. Native busy processing is not proven. `native_steering` stays `unknown`. `acp_steer_method` stays empty. The holder steer list was not changed. The after-turn holder queue and worker-result notification were not measured. They stay separate from this refusal.

## Other probes

Unknown id `--resume local-not-a-real-session-417`: `state` `error`, `acp_session_id` null, error `resume-failed`. The raw JSON-RPC error was `{"code": -32603, "message": "Internal error", "data": {"details": "not_found"}}`. It did not become a fresh session. The adapter `-32002` path (null result or a present mismatched `sessionId`) was not hit. The holder stayed up until `hermes stop` (`stopped` true).

Unservable `--model not-a-real-model`: start result `refused`, reason `model-config-option-rejected`, error `config-option-failed`, detail code `-32603`, `data.details` `model_resolution_failed`. Not local `-32602`. `state` was `ready` and a session was created: `local-1a627a45a6499ccfecaca86918c763663dbbd1e66364c57af1ee83f4e3d7c355`. Mode applied `dont_ask`; model applied false. That session was stopped. A later load still attached to the same id.

Cold `HERMES_HOME=/tmp/kpr-417-empty-home` (resolved `/private/tmp/kpr-417-empty-home`, distinct from `~/.hermes`): start `state` `error`, code `acp-initialize-timeout`, message `no initialize response`. It did not return `login-required` and did not name `hermes acp --setup`. Hermes bootstrapped a tree in that throwaway directory. The real home's initialize auth method `deepseek` is non-terminal, and the pong turn succeeded, so the DeepSeek credential on this machine was present. No login was performed.

## Stop and residual gateway rows

Exact stop of `hermes-kaola-i417-macbook` (`stop-main.json`): `stopped` true, `mutation_status` `completed`, `agent_exit_code` 0, `residual_pids` `[]`, `swept_child_pgids` `[]`. Status after stop: `state` `stopped`. No `hermes-kaola-i417` holder and no hermes tee remained after the follow-up viewers were stopped.

That ACP stop did not delete the gateway session rows. A later `session/load` of each id below returned `state` `ready` with the same id, and that viewer was then exact-stopped:

| Row | acp id | How it was created | Load after ACP stop |
|---|---|---|---|
| Main | `local-ecb75ab5174c39bd2421bc3b5155bf9b7af218ed55bc169f196cf0442efc31aa` | measured start | ready, same id |
| Preflight | `local-1e81c2e041666a59fbf51c93e6f3a3488f93c4810b0e9c6a70504a06cc9d6629` | installed-skill preflight (`initialize` + `session/new`, close capability false, child killed) | ready, same id; `currentModelId` still `auto:anthropic/claude-opus-4.6` |
| Bad model | `local-1a627a45a6499ccfecaca86918c763663dbbd1e66364c57af1ee83f4e3d7c355` | refused `set_model` after `session/new` | ready, same id |

Zero unintended residual sessions is not met as a deleted-row fact. These three rows are leftovers of this run. They were not removed.

The only profile gateway seen was pid 83083: `python3 -m hermes_cli.main --profile default gateway run --quiet --idle-exit`, started Wed Oct 28 23:15:23 2026, listen `127.0.0.1`, still alive after the ACP stops (elapsed about 19 minutes at the write-back check). It appeared in the window of this run's first `hermes acp` contact. There is no process snapshot from before that contact, so "hermes acp started it" is a correlation, not a before/after proof. No second gateway appeared. KPR did not run `hermes gateway stop`. Other holders on the machine were not touched.

`quit_text` was not measured (no quit command). It stays `unmeasured (source-read only; #417 measures live)`, and `scripts/adapters/hermes.sh` `ADAPTER_QUIT_TEXT` stays the same string. `continue_syntax` stays `unsupported` (`session/list` order was not measured).

## Mac Mini

Deferred. The Mini was offline and SSH was denied. This document does not transfer the MacBook receipts onto that machine. `acp_verified_versions` records the gap with `condition=macbook-20261028-mini-unmeasured`.

## What was not changed

No adapter edit. The live unknown-id and unservable-model frames did not hit the adapter's local `-32002` / `-32602` paths, and those paths stay as they are. No holder steer-list edit. No model-map or quota-rule edit. No worker grant.
