# Issue 264 — hooks lane delivery (Droid, Cursor CLI, DSH) — revision r3

Date: 2026-10-06. Lane: Worker-Class diagnostic lane `i264-host-chain-hooks-1035`
(holder `613aff918fd306d208fea7b4b982bb01`, session `opencode-KPR-i264-host-chain-hooks`).
Same assignment continuation. Workflow OFF. Writes only under
`/tmp/kpr-i264-host-chain-1035/hooks/**`. No claim, ledger, product write or acceptance.

Preserved revisions: `delivery-r1.md` (sha256 `d504e4c2…`), `delivery-r2.md`
(sha256 `55b6bb35f480b801912ff989dd08b9bbd563da23790d2cd3d7b61c1951a11940`).
All raw originals are kept; new evidence is in new subdirectories.

## 1. Host-accepted DSH result (unchanged, not repeated)

Host accepted the DSH positive explicit `/compact` result: native signal -> full installed
Project Runner/platform reads -> automatic typed duty -> automatic scoped verified recovery
`b-cd58270db6d3` -> exact reclaim. The r1 partial path remains valid. This revision does not
repeat DSH.

## 2. Provenance corrections

### 2.1 Cursor raw originals (corrected)

The r2 copies `cursor/host/receipts/raw/host-record.json` and `host-events.jsonl` were taken from
the OLD `cursor-KPR264HC-orchestrator-main` elite/no-prompt holder
`db96800f12802db2150f3223fa651d4d`. Those bytes are preserved with explicit naming:

- `raw/host-events.old-elite.db96800f.jsonl` (6 cursors, sha256 `de6800c7…`)
- `raw/host-record.old-elite.db96800f.json` (sha256 `01210b12…`)

Correctly bound actual-Host originals were added:

- `raw/host-events.actual-host.2d550c93.jsonl` (46 cursors, sha256 `941a65da…`)
- `raw/host-record.actual-host.2d550c93.json` (sha256 `41cfaf62…`)
- `raw/host-events.jsonl` and `raw/host-record.json` now point at the actual-Host copies.

Source of truth: `cursor/host/records/cursor-cli/cursor-cli-KPR264HC-orchestrator-main/af5cacf1299005e8/`,
holder `2d550c936613df3ad7a913bcbba5c6ed`, actual Host `end_turn`, no compact.

### 2.2 Droid prototype per-attempt binding (corrected)

The scratch prototype had TWO changed files (adapter and manifest), and the present tree names the
later probe `settings.json`. The present tree must not be bound retroactively to the original
attempt. Per-attempt pins are in `droid/receipts/prototype-pins.json`:

- Unchanged adapter `73a1059b…`; experimental adapter `6c831ad3…`.
- **The adapter patch was inert for both ACP attempts.** `adapter_build_launch` /
  `ADAPTER_LAUNCH_ARGS` are not called anywhere in the current candidate scripts; the ACP command
  is built by `manifest_launch_command`, which does not append launch args.
- Original attempt manifest `droid/host/manifest.droid.attempt.yaml`
  (sha256 `d6b09cafa0de933e7dd12f4efb71bee55c8f871fc8be65d73a2c8685d6ad1fba`) names
  `droid/host/droid-settings.json` (sha256 `23e47836…`).
- Probe manifest `droid/probe/manifest.droid.probe.yaml`
  (sha256 `00c14cfc3ab5c38da71afcfd2ec619f236b44811769c5f4e6f5bd2184049019f`) names
  `droid/probe/settings.json` (sha256 `8ef0b319…`).
- Observed applied argv for the original attempt (live `ps -o pid,args` on agent_pid 12156):
  `droid exec --output-format acp --settings /tmp/kpr-i264-host-chain-1035/hooks/droid/host/droid-settings.json`.

## 3. Droid — corrected source investigation and missing isolated Host attempt

Primary source (read-only): installed binary `/Users/ylmacstudio/.local/bin/droid` `@factory/cli`
0.233.0 sha256 `0e0bf625f7c45ade78fb5e11efcccaf4bcd00d53414e8e82b76c62969d0c1e34`; official
`https://docs.factory.com/droid-exec/overview`. Detail: `droid/source-findings-r3.md`.

Key findings:

- Accepted token-limit shape: `getDefaultCompactionTokenLimit(){...this.settings.general?.compactionTokenLimit…}`
  and `setDefaultCompactionTokenLimit(e){this.updateSettings({general:{compactionTokenLimit:e}})}`.
  The validation is on the daemon JSON-RPC `updateSessionSettings` path.
- Native manual compaction is a daemon/raw JSON-RPC method: `daemon.compact_session` /
  `droid.compact_session` (with `execute_rewind`, `fork_session`, `get_context_breakdown`). The
  official docs confirm the raw JSON-RPC surface can "compact history".
- The ACP sessionUpdate set includes `available_commands_update` and `current_mode_update`; the
  string `compaction_update` is ABSENT from the installed binary.

Missing isolated Host attempt (new, `droid/pos/`, one target, exact cleanup):

- Scratch manifest `droid/pos/manifest.droid.pos.yaml` (sha256 `8be97854…`) passed
  `--settings droid/pos/settings.json` (sha256 `144c2d0b…`) =
  `{"compactionThresholdCheckEnabled": true, "general": {"compactionTokenLimit": 4000}}`.
- Host `droid-KPR264HDP-orchestrator-main`, holder `a48e6ba005ad4e821ceb49bf210c58f6`,
  ACP `09180068-c527-4d43-b4dd-29c8c6a3b91e`, role `host`.
- Applied: only `compactionThresholdCheckEnabled` (`general` absent from the session settings
  snapshot). Context 14117 input tokens. No compaction and no ACP compaction variant.
- A business node started and was exact-stopped; host stop exit0/residual[].

Droid status: UNVERIFIED. The ACP runner has no located setting that lowers the threshold for an
ACP session; the token-limit key and native manual compaction live on the Factory daemon/raw
JSON-RPC surface, which KPR's ACP-only transport (#130) does not use.

## 4. Cursor CLI — corrected source investigation

Primary source (read-only): version dir files above; official
`https://cursor.com/docs/cli/reference/slash-commands` and `https://cursor.com/docs/cli/acp`.
Detail: `cursor/source-findings-r3.md`.

Key findings:

- `preCompact` producer: `index.js` ACP switch `case"preCompact"` maps
  `trigger:"manual"===e.trigger?"manual":"auto"` and calls
  `hookExecutor.executeHookForStep(Me._E.preCompact,t)`. Server-side decision; the local hook is a
  pre-compaction callback.
- ACP dispatch: `sendAvailableCommands()` advertises `loadCommands(...)` plus `copy-request-id`;
  `handleSlashCommand` special-cases only `/copy-request-id`; `resolveLeadingSlashCommand`
  resolves only against loader commands.
- `/summarize` (aliases `/compress`, `/compact`) is registered in the TUI command list
  (`6949.index.js`, `run → n.onSummarize?.()`), not in the ACP loader; the official docs list it as
  a terminal command only.
- Actual Host attempt exposed no compact/summarize command and no compaction variant.

Cursor status: UNVERIFIED. No client-reachable manual compaction trigger was located in the
installed build; the only KPR route is the project `preCompact` hook + notice CLI (unconfirmed).

## 5. Corrected claims (overbroad statements removed)

- Do NOT state that the Droid or Cursor native ACP surface "has no carrier". State instead: no
  completed signal was observed in the finite attempts, and the Droid binary lacks the
  `compaction_update` string; this makes a carrier unlikely in the installed build but is not
  proof that none exists.
- Do NOT state that "no manual trigger exists". State instead: no manual trigger is advertised in
  the ACP command list or CLI help; the source dispatch path resolves only the loader command set;
  whether a server-driven or future path can request compaction is unknown.
- The unsupported-key persistence probes do not by themselves establish a KPR production defect.

## 6. Limits and next recovery

- DSH positive chain3 verified for the explicit `/compact` route. Background automatic forwarding
  stays unverified. The r1 partial path stays valid.
- Droid and Cursor native completion, post-compaction read-use and Host chain3 remain UNVERIFIED.
- No confirmed KPR causal defect was found; no repository source change is proposed.
- Practical inquiry: ask Factory whether the ACP build exposes any completed-compaction
  notification or supported ACP compaction request; ask Cursor whether ACP exposes a compaction
  request or completion notification. Absent that, accept the project `PreCompact`/`preCompact`
  hook notice as the only KPR route and keep outcomes 1/3 unverified.

## 7. Evidence index (new in r3)

- `delivery-r1.md`, `delivery-r2.md` — preserved revisions
- `droid/source-findings-r3.md`, `cursor/source-findings-r3.md`
- `droid/receipts/prototype-pins.json` — per-attempt adapter/manifest/settings pins
- `droid/host/manifest.droid.attempt.yaml`, `droid/probe/manifest.droid.probe.yaml`
- `droid/pos/**` — corrected `general.compactionTokenLimit` Host attempt (raw events, record,
  settings, start/send/stop)
- `cursor/host/receipts/raw/host-events.actual-host.2d550c93.jsonl`,
  `host-record.actual-host.2d550c93.json`, and the `old-elite.db96800f` counterparts
- r2 evidence remains under `dsh-pos/`, `dsh-host/`, `droid/`, `cursor/`, `proto/`

## 8. Cleanup

- Droid pos host stop exit0/residual[]; its node exact-stopped `{stopped:true}`.
- All earlier targets/nodes remain stopped and were not restarted.
- OS query: no lane target process remains.
- Frozen worktree HEAD unchanged `4b247a2dbae9006be71962da32b31e5c5eb05629`; main repository has
  no tracked change; no write outside `/tmp/kpr-i264-host-chain-1035/hooks/**`.

## 9. Impact on the one Host-maintained table

Droid and Cursor cells stay UNVERIFIED with the corrected source findings and inquiry paths.
`receipts/table-row-proposals.md` carries the proposed wording. The Host owns the one table and
all selection/upgrade wording. No competing matrix.
