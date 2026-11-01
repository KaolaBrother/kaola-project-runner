# Issue #440 sandboxed kimi-cli 2.4.1 receipts

Verdict: GREEN for the measured ACP path. Pin update is authorized. Latest npm `@moonshot-ai/kimi-code` is 2.4.1. Native `kimi acp` has no public adapter package and no declared CLI range. Protocol stays 1. `acp_wrapper_pin` stays empty.

Sandbox: npm prefix `/tmp/kimi-241-prefix` (`@moonshot-ai/kimi-code@2.4.1`), command `/tmp/kimi-241-prefix/node_modules/.bin/kimi acp`. Fleet `kimi` stayed 2.2.0. `KIMI_CODE_SESSION_LOCK` was never set. No lock eviction and no `takeOverLock`.

## Launchd smoke (then discarded as the isolation proof)

`kpr440a` started ready on launchd. `agentInfo` Kimi Code CLI 2.4.1, protocol 1, capabilities `terminal:false` and `fs` read/write false. Model `kimi-code/kimi-for-coding`, thinking `max`, mode `yolo`, all configured. Send returned `turn_completed` / `end_turn` / final text `pong` (duration_ms 3526, tool_calls 0). Capture was 40 events (39 `session_update`, 1 `turn_ended`). Exact-stop `stopped: true`, residual `[]`.

Launchd does not forward `KIMI_CODE_HOME`, so that session was written under the user `~/.kimi-code`. After exact-stop, only that probe's session dir, its one `session_index.jsonl` line, the matching `workspaces.json` key, and four `.index-dirty` markers were removed. Later receipts use `--launch-backend direct` and `KIMI_CODE_HOME=/tmp/kimi-241-home`.

Preflight's catalog probe ran bare `kimi` on PATH (fleet 2.2.0) and reported `candidate_present: false`. The ACP initialize and `agentInfo.version` on the absolute 2.4.1 command are the pin evidence.

## Direct isolated matrix (authoritative)

Native session `session_211fd6ed-2bf8-428d-b01b-40576f061b31`. Repo `/tmp/kimi-241-repo`. Record root `/tmp/kimi-241-records`.

| Step | Session | Result |
|---|---|---|
| start direct | kpr440c | ready, agent 2.4.1, protocol 1, model/thinking/mode applied |
| send sleep, no-wait | kpr440c | `in_progress` |
| resume while owner turn runs | kpr440d | `state: error`, `resume-failed`, no `acp_session_id`. JSON-RPC `-32603` Internal error, `data.details`: "This session is in use by another Kimi Code CLI instance. Stop the session in that instance or exit it, then try again." |
| owner after that refusal | kpr440c | still ready, agent alive, mutation completed, `stop_reason: end_turn` |
| exact-stop refused client | kpr440d | `stopped: true`, residual `[]` |
| resume after idle | kpr440e | ready, same native id, error none |
| send "alpha" on original client | kpr440c | `turn_failed`, final text empty, tools 0, files 0. Error `{code: -32600, data: {code: "session.stale"}, message: "Invalid request: Session was updated by another client. Close and reopen the session, then retry."}` |
| durable `record.json` `turn_error` | kpr440c | `{code: -32600, message: <same>, source: "acp"}` — `data.code` dropped |
| send "beta" on loader | kpr440e | `turn_completed` / `end_turn` / final text `beta` |
| exact-stop original, resume again | kpr440f | ready, same native id |
| send "reopened" | kpr440f | `turn_completed` / `end_turn` / final text `reopened`, tools 0, files 0 |
| exact-stop kpr440e and kpr440f | both | `stopped: true`, residual `[]` |

The failed alpha prompt was not replayed. The second client did not obtain the session while the owner turn was in progress. Prompt-path `session.occupied` (`-32600` with `data.code` `session.occupied`) was not hit live: the second client was refused at resume/load before it could prompt. Source maps that prompt case to `-32600` with `data.code`. Cancellation, permission, and compact were not exercised.

JSON files in this directory are the raw receipts. Do not print credential fields from them.
