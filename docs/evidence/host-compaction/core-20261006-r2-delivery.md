# Issue 264 mission 6 — core lane delivery r2 (Codex / Grok CLI / OpenCode)

Date: 2026-10-06/07. Lane: `/tmp/kpr-i264-host-chain-1035/core`. Frozen
candidate: `.kw/worktrees/issue-259` HEAD `4b247a2d` (behavior ≡ `291b33b5`).
This revision preserves `delivery-r1.md` and all original run records; it adds
causal source traces, the Codex transport boundary probe, corrected provenance
for the deleted contaminated Codex attempt, and one finite positive counterpart
run for the recovery-checkpoint seam. Workflow OFF; nothing outside
`core/**` was written. No product mutation was applied — the single candidate
behavioral fix is a scratch proposal for Host custody (§2.4).

Verdict frame: r1 measured the full native-signal → duty → node → checkpoint →
reclaim chain on all three runtimes with real evidence, but three outcomes
remain unverified or partial — Codex automatic Skill reread (transport-bound),
and all three recovery checkpoints (`recovery-entry-unknown`). This delivery
resolves the cause of each partial, proves the checkpoint contract is
reachable through the normal automatic carrier, and pins the Codex hook
boundary to the App-Server transport.

## 1. Seam 1 — why every recovery checkpoint was `partial`

### 1.1 The actual emitted entry

Raw `--entries` argument recovered from each node's own ACP tool-call stream
(original `node-events-all.json`, not the normalized checkpoint projection):

| Runtime | node2 holder | batch | raw entry (top-level keys) | Host event cursor |
|---|---|---|---|---|
| Codex | `e1f8fbd3f188` | `b-90965c51ce82` | `input, checked{auth[8],duties[9],links[8]}, unavailable{}, retained` | argv at node cursor 945 |
| Grok | `030c3132ad9e` | `b-a3222b0e394e` | `input, checked{auth[3],duties[5],links[6]}, retained` (no `unavailable` key) | argv at node cursor 872 |
| OpenCode | `2b57e8c09a0a` | `b-a2f62de87573` | `input, checked{auth[6],duties[5],links[5]}, unavailable{}, retained` | argv at node cursor 1213 |

All three emitted `"retained": "tasks/qa-observe"` on the `recovery#1` input.
`checkpoint_entry()` (`kaola-dispatch.py` ~L4794-4817, sha256 `140d1399…`)
rejects any `recovery#` entry whose keys exceed
`{input, checked, unavailable, applied}` → `recovery-entry-unknown`, returned
truthfully as a partial checkpoint. The `seq` key seen in
`last_checkpoint.recovery` is the tool's own receipt echo (constructed at
~L4934-4937), not a node-emitted field — Host1059's correction
(`host-checkpoint-causal-correction-1059.md`) independently parses the same
three raw commands and confirms `retained` is the offending key.

No scope conflicts existed in any of the three entries: `checked` carried
complete authorization/duties/links scopes and `unavailable` was empty or
absent (the contract treats a missing `unavailable` as empty). Had
`retained` been absent, the entries satisfy the contract — and edge-lane
ZCode cursor 1401 proves it empirically: `input`+`checked` only, settled
`recovery#1` **verified**.

### 1.2 Causal source — shared prompt artifact, not a model quirk

- `_node_prompt()` (`kaola-acp-holder.py` L3707-3742, sha256 `d8cc9dc1…`)
  emits, for EVERY batch, a generic contract paragraph: "Use `retained` for
  an unchanged Host record with `next`, `owner` or `wait`" plus example
  `{"input": ID, "retained": "tasks/ID" or "section/NAME"}` (L3720-3728).
- The same prompt's recovery paragraph (L3729-3742) then names the recovery
  shape — `input`, `checked:{authorization,duties,links}`,
  `unavailable:{scope:reason}` — but never states that `retained` (or any
  other key) is forbidden on a `recovery#` entry.
- `state checkpoint --help` advertises only `applied`/`retained` shapes; no
  recovery exception appears there either.
- Installed node guidance (`sideagent-node.md` L75-85) likewise advertises
  `applied`/`retained` for ordinary entries without naming the recovery
  exclusion; `duty-reconcile.md` L115-129 shows the correct recovery shape
  but does not explicitly forbid `retained`.

Three different models (gpt-6.1-sol, grok-4.7, deepseek-v4.1-flash)
independently merged the generic `retained` guidance onto the special entry —
a deterministic guidance-conflict signature, not runtime behavior. The schema
is correct and stays unchanged; the prompt/guidance corpus is ambiguous.

### 1.3 Replay boundary

`_node_recovery_pending()` suppresses an already-returned recovery sequence
(`kaola-acp-holder.py` ~L3473: "a scoped request creates the next input; it
does not replay a failed or unknown batch"). `recovery#1` in each original run
was returned — truthfully partial — and will not be re-sent. A truthful
positive counterpart therefore required a fresh finite run producing a new
`recovery#1`, not a replay.

### 1.4 Positive counterpart — r2 run (controller-assisted setup, labeled)

Method: identical driver and frozen sources; fresh disposable consumer under
`core/opencode-r2/`; ONE project-local guidance item appended to the fixture
`AGENTS.md` user requirements (read by nodes — original runs show them
listing/grepping it): the `recovery#N` entry accepts only
`input`/`checked`/`unavailable`/optional `applied`, `retained` never applies.
This corrects guidance INPUT to the model under test; it changes no schema,
no source, no installed Skill — labeled controller-assisted setup, never
production efficacy.

Result (opencode-r2, measured 2026-10-06 ~11:15-11:21Z): **VERIFIED
counterpart.**

- Real signal: `compact_reload_detected` cursor 33, occurrence
  `msg_110ecc4590011MMtxrqh8LaPyx` → `compact_reload_delivered` cursor 35 →
  `host_compact_maintenance_registered` cursor 36 (typed `recovery#1`, source
  `completed-host-signal`, evidence bound to host events.jsonl#33).
- Automatic node at a safe boundary: `sideagent_node_started` cursor 246
  (holder `78b091356d072e3038c2db8e2ad6f247`), recovery-only batch
  `b-cb3b9280f581` at cursor 247.
- The node's raw `--entries` (node event cursor 789): `recovery#1` with keys
  `input` + `checked` ONLY — complete refs (auth[6], duties[5], links[4]),
  `--recovery-seq 1` passed as the flag (not an entry key), no `retained`,
  `unavailable` omitted as the contract permits. `sideagent_node_settled`
  cursor 248: `checkpoint: "verified"`, `settled: ["recovery#1"]`,
  `verified: true` in `last_checkpoint` (batch `b-cb3b9280f581`,
  11:21:06Z).
- Exact reclaim: `sideagent_node_stopped` cursor 253; Host stop exit 0;
  `residuals: []`.

This is the smallest truthful positive: the same frozen schema, same holder
prompt, same automatic carrier produced a verified scoped checkpoint once the
guidance input no longer invited `retained`. It is controller-assisted setup
— it does NOT establish production efficacy of an unmodified prompt; the
original three partials stand as the product's out-of-box behavior. Per-owner
scope, Grok/Codex were not re-run for this seam: the defect is in the shared
prompt text, not runtime-specific; the Host decides whether per-runtime
repeats are wanted.

## 2. Seam 2 — Codex hook invocation path and the transport boundary

### 2.1 Actual mechanism (Codex 0.160.1, adapter codex-acp 2.0.1)

- `@agentclientprotocol/codex-acp@2.0.1` spawns `codex app-server`
  (App-Server JSON-RPC), not the TUI. Adapter `dist/index.js` sha256
  `2729d2a39c9fde47c494828a76c7eb2fabc0f9940f2723183426c1afbf1a5e7d`
  (three identical npx-cache copies); child binary
  `/Users/ylmacstudio/.local/bin/codex` sha256
  `61b0194f3bb6534439c8d26a3ed57d0805f84b884588b761795323eeb92fcf70`,
  package version 0.160.1 (requested 0.160.0).
- Codex discovers hooks from `$CODEX_HOME/hooks.json`, plugin dirs, and
  project `.codex/hooks.json` — the project layer only for a **trusted**
  repository; each hook entry additionally needs a `hooks.state` record whose
  `trusted_hash` equals the entry's `currentHash` (computable via the
  App-Server `hooks/list` RPC). Untrusted hooks are skipped silently.
- `session/compact` maps to App-Server `thread/compact/start` in the adapter.

### 2.2 Original run's actual blockers (now evidenced, not inferred)

- The disposable repo WAS project-trusted: codex itself persists
  `[projects."<repo>"] trust_level="trusted"` into `~/.codex/config.toml`
  (entry present for `core/codex/run/repo`).
- The project hook had NO `hooks.state` `trusted_hash` record → status
  `untrusted` → skipped even if invoked.
- Structurally decisive: the ACP/App-Server compaction path never dispatches
  the hook engine at all (2.3). Both layers independently sufficient.

### 2.3 Disposable per-process probe (`core/codex2/`)

Supported route only: lane-local `CODEX_HOME=core/codex2/codex-home` +
`codex app-server` + project `.codex/hooks.json` in disposable repo
`core/codex2/repo`. No global edits, no trust bypass, no install/login.
Probe: `core/bin/probe_codex_hooks.py`; receipts `core/codex2/receipts/`.

Observed:
- `hooks/list` (receipt 02): both project hooks discovered, `untrusted`,
  codex-reported `currentHash` `sha256:3f1598…` (postCompact),
  `sha256:e525d6…` (sessionStart compact matcher).
- Trust persisted into the LANE config.toml using those exact reported hashes
  (what `/hooks` review would write) → re-list shows `trusted`+`enabled`
  (receipt 03).
- `thread/compact/start`: real `contextCompaction` item ran
  (`item/started`→`item/completed`, turn ≈19.4 s, receipt 06/10) and a real
  follow-up turn ran to completion — **zero** `hook/started`/`hook/completed`
  notifications, no PostCompact marker, no SessionStart marker (receipt 07
  empty; `postcompact-fired.json` absent at that stage).
- Native TUI on the SAME lane home/repo (`/compact`, manual): PostCompact
  fired — `postcompact-fired.json` (410 B): `hook_event_name:"PostCompact"`,
  `trigger:"manual"`, real `session_id` `01a110e1-…`, `turn_id`, transcript
  path, model `gpt-6.1-sol`. The NEXT TUI turn fired
  `SessionStart(source:"compact")` — `sessionstart-fired.json` (390 B), same
  session id, `permission_mode:"default"`.

Conclusion (transport-scoped, both halves measured):
- Codex 0.160.1 native TUI: `PostCompact(manual)` AND `SessionStart(compact)`
  fire correctly for a trusted project hook. Hook machinery works.
- Codex 0.160.1 ACP/App-Server (`thread/compact/start`, the only transport
  codex-acp 2.0.1 uses): hook dispatch never occurs — trusted+enabled project
  hooks did not run during compaction or the following turn.
- Therefore the KPR Codex Host (always ACP) cannot receive a native
  `SessionStart(compact)` on this transport/version: outcome-2 stays
  **unverified for Codex**, bounded to "ACP/App-Server on 0.160.1 + adapter
  2.0.1". The TUI positive is a boundary marker, not substitute evidence.

### 2.4 Scratch patch proposal (Host custody — NOT applied)

`kaola-acp-holder.py` L1152 + L4189-4195: `NATIVE_COMPACT_RECOVERY_PLATFORMS
= frozenset({"codex"})` rests on the assumption "the current Codex ACP Host
receives the KPR-USER-COMPACT-RECOVERY-V1 marker and fully rereads its
installed main Skill on that path". Measured: on the only transport a Codex
ACP Host can run (app-server), no hook fires, so nothing owns the reread —
the holder records `compact_reload_native_owned` and skips the ACP-driven
reload that every other runtime receives. Smallest candidates:

```diff
- NATIVE_COMPACT_RECOVERY_PLATFORMS = frozenset({"codex"})
+ NATIVE_COMPACT_RECOVERY_PLATFORMS = frozenset()
```

→ Codex Hosts get the same `compact_reload_delivered` bounded reload prompt
as Grok/OpenCode; the TUI hook path remains correct for non-ACP Codex use.
Variant (if TUI coverage must be preserved selectively): gate on transport —
remove codex from the set only when the holder's transport is the codex-acp
adapter. Affected-verification plan: rerun exactly this lane's Codex chain —
expect `compact_reload_delivered`, automatic installed-Skill reread
evidence, and identical duty/node behavior. The project-hook install remains
harmless and correct for TUI-attached sessions.

### 2.5 Preserved separations

The post-compaction Codex continuation read `workflow-next/SKILL.md` — a
controller-assisted manual read (driver prompt), NOT an automatic KPR reread;
kept as separate evidence, never counted toward outcome 2.

## 3. Seam 3 — contaminated Codex attempt provenance

Source: Host's original worker capture `/tmp/kpr-1056-core-original-capture.json`
(platform devin, session `devin-KPR-i264-host-chain-core`, 5110 events,
level L3). The capture preserves terminal echoes of the deleted records; the
records themselves were removed and are NOT reconstructed here as measured
evidence.

### 3.1 Exact identities

| Attempt | driver cursor/ts | Host holder | ACP session | holder/agent PID | node |
|---|---|---|---|---|---|
| run A (leaked) | 2544 / 17:29:52 | `0dc27ac16bdf545df9765141b49a2517` | `01a1108d-19c3-7c12-bd8d-067ea2176498` | 60560 / 60561 | node `77ac46e8dcef6515af96f87b24887df8`, batch `b-cf6bfd1a3bcb` |
| run B/C (contended) | 2680 / 17:30:42 and 2754 / 17:31:56 | `c6a6351159fef6a723a85e1644f4c173` | `01a1108e-4034-7f72-ba93-beaead9ea661` | 79357 / 79358 | node `0d5d410b5e44272fda26a7af239b75ce5`, acp `01a11092-7e2f-…` |
| clean run (measured) | 3912 / 17:36:12 | `c0c935cbaee999d195a44ab3b1d53af0` | `01a11098-40c1-7723-8928-a32b882c4d09` | — | nodes `daf020e8ad1d`, `e1f8fbd3f188` |

Attribution limit, stated honestly: three `rm -rf codex && drive_lane.py`
invocations occurred within ~2 min (capture cursors 2544/2680/2754). Exactly
two Host ACP sessions ever existed (`01a1108d`, `01a1108e`); the middle
invocation's driver output was deleted by the next `rm` before observation,
so which of B/C produced `c6a635` is not recoverable from the capture.

### 3.2 Mechanism of contamination

Driver A's buggy `result`-vs-`state` check exited before its `finally`
cleanup → holder `0dc27ac` stayed live. Driver B's `rm -rf codex` then wiped
the lane dir (fixture + `run/records/**`) WHILE A's holder was mid-start;
both holders consequently shared record dir
`records/codex/codex-KPR1035C-orchestrator-main/1eb0bc62e7c7029a`, each
overwriting `record.json` → `host-identity-required` refusals (capture
cursors 2837-2923), a premature `sideagent_node_lost` for run-A's node
`77ac46e8` at its own event cursor 10-11 (ts 1791279122) — even though that
node's checkpoint had already settled all four records `verified` at
09:33:16Z (capture cursor 2837) — and `binding-or-recipe-unavailable`
follow-on failures. Run-B's node `0d5d410b` similarly faced flipped record
identity.

### 3.3 Actions and removals (all from capture)

- `rm -rf codex` at cursors 2461, 2522 (fixture dry-runs), 2544, 2680, 2754
  (the three racing driver invocations), 3912 (clean re-run). Each deleted
  the whole `core/codex/` tree: records, event logs, receipts.
- Exact-stop: `kill 60560 79357 46913` (TERM) at cursor 3199 ts 1791279526 —
  targeted PIDs only; no broad process kill.
- Irrecoverably missing: run A/B/C per-phase receipt files
  (`receipts/0*.json`), their raw `events.jsonl` streams, driver stdout of
  the middle invocation, and run-A's node stream. What survives is only
  what the Host's own stream echoed (quoted above) plus the deleted-runs'
  node checkpoint projection visible at capture cursor 2837.
- The clean run's results (delivery §measured) are the only measured Codex
  row; contaminated-run fragments are provenance, not evidence.

### 3.4 Receipt locator correction

Per-run summary receipts are `core/<plat>/receipt.json`
(`core/codex/receipt.json`, `core/grok/receipt.json`,
`core/opencode/receipt.json`, `core/opencode-r2/receipt.json`) — not
`receipts/receipt.json`. Exact node stops are `sideagent_node_stopped` Host
events (codex cursors 83/353, grok 131/1384, opencode 30/152) plus each
`09-host-stop.json` and the `residuals` field inside each per-run
`receipt.json`. No `10-node-stop.json` was ever written (driver only writes
it if a node outlives the Host stop — all nodes were already exact-stopped
by the holder; the index naming was wrong, now corrected).

## 4. Versions, selections, hashes

| Runtime | requested | applied native selection | adapter/transport | hashes |
|---|---|---|---|---|
| Codex | CLI 0.160.0 | child `@openai/codex` 0.160.1, model `gpt-6.1-sol`, effort high, mode agent-full-access, fast off | `@agentclientprotocol/codex-acp` 2.0.1 → `codex app-server` | adapter dist/index.js `2729d2a3…`; child bin `61b0194f…` |
| Grok CLI | default | `grok-4.7`, reasoning `xhigh`, fast not advertised | native `grok agent --always-approve stdio` | bin `e8daa302…` (grok-1.0.46-macos-aarch64) |
| OpenCode | default | `opencode-go/deepseek-v4.1-flash` applied (catalog lists `opencode/deepseek-v4.1-flash`; prior Fledge selection is a DISTINCT earlier run), effort no-resolved-value, fast not advertised | `kaola-opencode-acp.py` → `opencode acp` | adapter `47a3b97d…`; bin `e7bef8c3…` (v2.0.23) |

Frozen candidate pins (sha256): holder `d8cc9dc1…`, dispatch `140d1399…`,
compact-recovery `c45662a4…`, codex-compact-hook `c21e463e…`, tmux
`b03d9fca…`, opencode-acp `47a3b97d…`. Capability negotiation evidence:
Codex initialize carried `clientCapabilities.session.compaction={}`
(receipt `02c-negotiation.json`) — the candidate fix the installed holder
lacks.

## 5. Updated capability rows (core three only)

| Runtime | O1 native completed signal | O2 automatic Skill reread | O3 Host duty→node→checkpoint→reclaim |
|---|---|---|---|
| Codex 0.160.1/acp2.0.1 | VERIFIED (compaction_update completed, cursor 88) | UNVERIFIED on ACP transport — TUI-verified hooks do not fire under `thread/compact/start`; patch proposed §2.4 | Chain VERIFIED; checkpoint PARTIAL (`retained` key); positive counterpart proven on OpenCode §1.4 |
| Grok CLI 1.0.46 | VERIFIED (auto_compact_completed, cursor 136) | VERIFIED (installed reads byte-exact 17407/10193 B) | Chain VERIFIED; checkpoint PARTIAL (same cause); counterpart §1.4 |
| OpenCode 2.0.23 | VERIFIED (opencode/compaction, cursor 33, msg_110bb…) | VERIFIED (installed reads byte-exact 17407/10597 B) | Chain VERIFIED; original checkpoint PARTIAL, **r2 counterpart VERIFIED** (`recovery#1` settled, batch b-cb3b9280f581, cursor 248) |

All-runtime verification remains OPEN: seven runtime rows are owned by other
lanes; Codex O2 and the production-efficacy question for the guidance fix
remain with the Host.

## 6. Cleanup / residuals

- Original three Hosts + six nodes: `sideagent_node_stopped` events at the
  cursors above; `09-host-stop.json` per runtime; `residuals: []` in each
  `core/<plat>/receipt.json`.
- codex2 probe: App-Server daemon + pid-update-loop exact-stopped (PIDs
  56139/56168); TUI tmux session killed; lane `CODEX_HOME` only — no global
  config touched.
- opencode-r2: `sideagent_node_stopped` cursors 30/253;
  `09-host-stop.json` stopped:true exit 0; `residuals: []` in
  `core/opencode-r2/receipt.json`.
- `pgrep KPR1035C`: clean after all runs (edge-lane kimi holder excluded —
  not this lane's process).
