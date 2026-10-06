# Issue 264 — hooks lane delivery (Droid, Cursor CLI, DSH) — revision r2

Date: 2026-10-06. Lane: Worker-Class diagnostic lane `i264-host-chain-hooks-1035`
(holder `613aff918fd306d208fea7b4b982bb01`, session `opencode-KPR-i264-host-chain-hooks`).
This is the Host review continuation of the same assignment, not a new lane.

Scope: DSH positive-chain counterpart, plus new actual Host-role attempts for Droid and
Cursor CLI. No claim, no mission ledger, no product write, no acceptance, no lifecycle action.
Workflow remains OFF. All writes stay under `/tmp/kpr-i264-host-chain-1035/hooks/**`.

Original revision r1 is preserved byte-for-byte at `delivery-r1.md`
(sha256 `d504e4c275ec2a10a84bab7113145700145d196f1f9db50fe924f562eaca3d3b`).
The original negative/partial run and its raw receipts are unchanged under `dsh-host/`.

## 1. Host review qualification of r1

The Host correctly qualified the r1 claim:

- R1 proved automatic activation + visible partial recovery + exact reclaim on DSH.
- R1 did NOT prove a SUCCESSFUL verified scoped recovery checkpoint.
- Cause: the r1 seam seeded an unresolved dispatch ref (`qa-gap-missing`) with no original, so
  the node honestly returned `links` unavailable and the checkpoint stayed `partial`.

This revision keeps that negative path intact and adds a new positive seam on a new consumer.

## 2. Candidate, runtime and Skill identity

- Frozen accepted source: `.kw/worktrees/issue-259` HEAD
  `4b247a2dbae9006be71962da32b31e5c5eb05629`. Exact transport source used:
  `/tmp/kpr-i264-host-chain-1035/hooks/candidate` (same bytes).
- Candidate script hashes (measured): holder `d8cc9dc147f69db50dc5be5c7cf1f7efced677c19813155792a191aedb72f280`,
  compact recovery `c45662a4…e90f27`, DSH adapter `b1879fca…c506e6a`, dispatch `140d1399…45c6fbfd`,
  tmux `b03d9fca…3be5b8b`.
- Installed Skills at dispatch:
  - `kaola-project-runner/SKILL.md` 17407 B / 264 lines / sha256 `1af732f378a11bd04e4533a3e1fe38cef9b9b48b393360748d0a8030f5524df7`
  - `dsh-kaola-project-runner/SKILL.md` 10450 B / 165 lines / sha256 `ea2ccfbd2c523baebb6f6ff7a5b41654b08922bd379f52f35770d7c00098db22`
  - `droid-kaola-project-runner/SKILL.md` 10365 B / sha256 `d99d5e4f09a22f73f472b8b076a0eb0c3ef817b5160d8527d1280918be0c0fad`
  - `cursor-cli-kaola-project-runner/SKILL.md` 10486 B / sha256 `2a4dafef90d91ce0df0dd9c7137800bd7f83bbac3e53d9663950ad25031595cf`
- Runtimes: DSH `0.2.0-rc.2`; Droid `0.233.0`; Cursor CLI `2026.09.28-64d2043`.

## 3. DSH positive-chain counterpart — VERIFIED

New isolated disposable consumer: `/private/tmp/kpr-i264-host-chain-1035/hooks/dsh-pos/consumer`.
Separate record root `hooks/dsh-pos/records`. Dispatcher and heartbeat environment scrubbed.
Seeded truthfully: project `KPR-I264H2-DSH`, authorization grant `qa-node`, a diagnostic task
`qa-observe` with ONE resolvable child dispatch `qa-prior-reclaim-1` (real prior-run receipts),
and NO unresolved gap. State seeded before the native signal.

Host session `dsh-KPR264H2-orchestrator-main`, role `host`, holder
`f9d9d2344dae9b4d0c919dac478d55ad`, ACP session `0722b754-2773-40fe-ab41-61d448f9eab4`.

Stage status, in order (host `events.jsonl`; raw copy
`dsh-pos/receipts/raw/host-events.jsonl`):

1. Business batch (pre-signal, automatic): cursor 13 node start `79ae3825081f16bef4cf0f7a857dd229`,
   cursor 14 batch `b-1bbb78d27b63` through revision 4, cursor 15 settled `verified`,
   cursor 20 exact stop. This is business reconciliation, not recovery.
2. Native completed signal (explicit `/compact`): cursor 22 `compact_reload_detected`, role
   `host`, occurrence `506d74ee-f23c-4d34-848a-9cf64e4af77b`, sourceCommandId
   `4427aebe-6fc8-49c8-8d02-df59675f0c8a`, `summarySeq 26`, `endSeq 28`,
   `shadowedRange {8,19}`, `shadowedTokenCount 4083`.
3. Independent typed recovery duty (automatic): cursor 25
   `host_compact_maintenance_registered`, signal_cursor 22, `recovery-input seq 1`,
   kind `host-compaction`, source `completed-host-signal`, holder-bound. No business revision
   change, no remembered Host request, no fake edit.
4. Skill reload (automatic): cursor 24 `compact_reload_delivered`. In that turn the Host fully
   read the current installed Skills (read cursors 36/37, results 38/39: 264 lines and 165
   lines) and continued TASK-B (progress re-read 145/161, updated at 162).
5. Recovery node at safe boundary (automatic): cursor 167 node start
   `4d56cdc70f155f3b56692c79a9bf4ab6`, cursor 168 batch `b-cd58270db6d3` with
   `recovery_input seq 1`, `host_revision_through 6`.
6. VERIFIED scoped checkpoint: cursor 169 `sideagent_node_settled`, batch `b-cd58270db6d3`,
   checkpoint `verified`, `checkpoint_through 6`, `host_woken false`. The saved checkpoint shows
   `checked.authorization`, `checked.duties` and `checked.links` all with non-empty real refs;
   `unavailable: {}`; `returned_to_host: {}`; `settled` includes `recovery#1`;
   `last_checkpoint.verified: true`; `last_verified` names the exact batch and node holder.
7. Exact reclaim: cursor 174 `sideagent_node_stopped` receipt `{stopped: true}`; node record
   `state: stopped`, `agent_alive: false`.
8. Target reclaim: host stop `{stopped: true}`, `agent_exit_code: 0`, `residual_pids: []`.

Smallest positive-chain counterpart result: PASS. One real native `/compact` produced a full
installed-Skill reload plus distinct TASK-B continuation, an independent automatic typed
recovery duty, a scoped holder/batch/source-bound VERIFIED recovery checkpoint, and exact
node/target reclaim. Raw receipt: `dsh-pos/receipts/dsh-positive-chain-receipt.json`.

## 4. Droid 0.233.0 — actual Host attempt, UNVERIFIED

Concrete investigation first (installed primary source), then one useful actual attempt.

- `droid --help` / `droid exec --help`: no compact, compress or summarize command.
- Installed binary (mmap, read-only) contains `compactionThresholdCheckEnabled`,
  `compactionTokenLimit`, `compactionTokenLimitPerModel`, `compactionLimitSelector`,
  `PreCompact`, `[Compaction] PreCompact hook blocked compaction`, `hooks.json`.
- The ACP command built by the runner carries no launch flags. This lane used a scratch-only
  prototype candidate under its lane to test one concrete per-process route: a patched scratch
  manifest `acp_command` adding `--settings <file>`. Pinned scratch bytes:
  unchanged adapter `73a1059b0f0d04a017600280583ba3516896ef0ed642a6d867436d233bc5ba51`,
  prototype adapter `6c831ad3b65995c4bfde515910fdd04df5873072f1b5a5d79e1e28c6b3a87a28`.
  This is a diagnostic prototype only, not repository or product custody.

Actual Host attempt: `droid-KPR264HD-orchestrator-main`, holder
`fbc5e43941d311b51933918a2af68ac4`, ACP `04d98bf9-6c68-4bd2-8602-8646df495b43`, role `host`.
The agent process args confirm `--settings` was passed.

Findings:

- `compactionThresholdCheckEnabled: true` WAS applied (persisted in the native session settings).
- `compactionTokenLimit`, `compactionTokenLimitPerModel` and `compactionLimitSelector` did NOT
  persist as settings-file keys (probe2 applied only the boolean).
- Context reached `tokenUsage.inputTokens 20706` (`lastCallTokenUsage.inputTokens 5241`).
- No native compaction occurred. ACP session_update variants were only
  `available_commands_update`, `current_mode_update`, `config_option_update`, `tool_call`,
  `tool_call_update`, `agent_message_chunk`. No `compaction_update` and no native compact signal.
- `availableCommands` (33 entries) contain no compact or summarize command.

Smallest concrete still-unverified gap for Droid: the installed ACP surface exposes
`compactionThresholdCheckEnabled` but no accepted per-process custom compaction limit, and the
Droid native ACP stream carries no completed-compaction carrier. The only KPR-recognized Droid
route remains the project `PreCompact` hook + `kaola-project-compact-notice.py` (an unconfirmed
notice, never a completed signal). Host source repair requested: expose a verified supported
compaction limit through the runner, or confirm whether a native completed ACP carrier exists.

## 5. Cursor CLI 2026.09.28-64d2043 — actual Host attempt, UNVERIFIED

- `cursor-agent --help`: no compact, compress or summarize command.
- Installed source `index.js` sha256 `0d0c83f5478c3dcd806cb9697123cee3f548005fbcd3acafe31f102d659f5a7b`
  has a real `preCompact` hook with `trigger(manual|auto)`, `context_usage_percent`,
  `context_tokens`, `context_window_size`, `message_count`, `messages_to_compact`,
  `is_first_compaction`. `/compress` matches were unrelated connectrpc compression. No
  configurable compaction threshold was found in the CLI source.
- Actual Host attempt: `cursor-cli-KPR264HC-orchestrator-main`, holder
  `2d550c936613df3ad7a913bcbba5c6ed`, ACP `4d82cf8e-dbb7-4f71-83d4-569cbd2f37b8`, role `host`,
  applied selection grok-4.7 / xhigh / Fast `false`. One bounded turn completed.
- The ACP `available_commands_update` enumerated 40+ commands; NONE is compact or summarize.
- Session_update variants: `available_commands_update`, `session_info_update`,
  `agent_thought_chunk`, `agent_message_chunk`, `tool_call`, `tool_call_update`. No compaction
  variant and no compact mention.

Smallest concrete still-unverified gap for Cursor: there is no client-reachable manual
compaction trigger in the installed CLI/ACP surface, and no configurable local threshold. The
only local route is the `preCompact` project hook, which requires the runtime/server to actually
compact. Host source repair requested: confirm whether any supported ACP manual compaction
trigger exists, or accept the hook-only unconfirmed route.

## 6. Limits and honest qualifications

- DSH positive chain3 is verified for the explicit `/compact` route on DSH `0.2.0-rc.2`.
  Background automatic compaction forwarding stays unverified.
- The r1 partial/negative recovery path is retained and is valid evidence, not a defect.
- Droid and Cursor native completion, post-compaction read-use and Host chain3 remain
  UNVERIFIED. Both are unverified, not unsupported. Each has a concrete source/attempt outcome.
- The Droid scratch prototype is diagnostic only. It is not a repository change, not installed
  and not product custody.
- No installation, login, account/model/tier switch, timer or consumer mutation occurred.
- One diagnostic target ran at a time. All new targets and nodes are stopped.

## 7. Evidence index

Under `/tmp/kpr-i264-host-chain-1035/hooks/`:

- `delivery-r1.md` — preserved original delivery (sha256 `d504e4c2…`)
- `receipts/hooks-r2-verification.json` — machine summary of all three runtimes
- `receipts/table-row-proposals.md` — proposed table rows (not a repository write)
- `dsh-pos/receipts/dsh-positive-chain-receipt.json` and `raw/host-events.jsonl`,
  `raw/node-events.jsonl`, `raw/state-heartbeat-prompt.json`, `host-start.json`,
  `host-send-seed.json`, `host-send-compact.json`, `host-stop.json`
- `dsh-host/**` — original r1 run (unchanged)
- `droid/host/receipts/` — Droid host start/send/stop, raw events and session settings
- `droid/probe/receipts/` — Droid settings-key probe
- `droid/try/` — Droid `--list-tools` settings acceptance checks
- `droid/droid-binary-compaction-symbols.json` — binary symbol extraction
- `cursor/host/receipts/` — Cursor host start/send/stop and raw events
- `cursor/cursor-native-source-match.json`, `cursor/kpr-heartbeat726-cursor-native-boundary-excerpts.json`
- `proto/candidate/` — pinned scratch prototype candidate; `proto/patch_droid_adapter.py`

## 8. Cleanup

- DSH positive host stop exit0/residual[]; node exact-stopped.
- Droid attempt host stop exit0/residual[]; probe host stop exit0/residual[].
- Cursor attempt both sessions stop exit0/residual[].
- OS query: no lane target process remains; no `kpr-droid-settings.*` temp files remain.
- Frozen worktree HEAD unchanged `4b247a2dbae9006be71962da32b31e5c5eb05629`; main repository has
  no tracked change. No write outside `/tmp/kpr-i264-host-chain-1035/hooks/**`.

## 9. Impact on the one Host-maintained table

This revision adds: one measured DSH positive chain3 (verified) entry, one Droid
`compactionThresholdCheckEnabled` applicability finding with an unverified native route, and one
Cursor `preCompact`-only unverified route. Proposed rows are in
`receipts/table-row-proposals.md`. The Host owns the one versioned table and all
selection/upgrade wording. No competing matrix is created.
