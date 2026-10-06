# Core-lane delivery — issue 264 mission 6 (Codex, Grok CLI, OpenCode)

Date: 2026-10-06. Lane: `core` of `/tmp/kpr-i264-host-chain-1035`. Scope:
three runtimes on the frozen candidate transport, disposable consumers only.
This delivery reports measured results. It does not close the issue, change
the repository, or write the owner capability table. The values below are
row contributions for the single owner-maintained table.

## 1. Test object identity

| Item | Value |
|---|---|
| Candidate source | `.kw/worktrees/issue-259` @ `4b247a2dbae9006be71962da32b31e5c5eb05629` (export in `core/src`, zero diff vs `291b33b5`) |
| Holder | `scripts/kaola-acp-holder.py` sha256 `d8cc9dc147f69db50dc5be5c7cf1f7efced677c19813155792a191aedb72f280` |
| State tool | `scripts/kaola-dispatch.py` sha256 `140d13992f1749b003c69222c3d6f714bdf8e5e9c7db19ed7e84c05245c6fbfd` |
| Signal module | `scripts/kaola-compact-recovery.py` sha256 `c45662a4297047bd860a46157e950b4aac460b3e9df1a889abe99ca687e90f27` (same blob as the 862 receipt) |
| Codex hook | `scripts/kaola-codex-compact-hook.py` sha256 `c21e463e5b2bc69609347b220124197c4719b3607525e5a518b3e13318462682` |
| Runner | `scripts/kaola-tmux.sh` sha256 `b03d9fca3ded8f98bad7788c175f76da2815ca85aeeb9ebd25d7721283be5b8b` |

Measured installed runtimes:

- Codex CLI `0.160.1` (manifest requests `0.160.0`; resolution selected the
  installed `0.160.1`), ACP adapter `@agentclientprotocol/codex-acp@2.0.1`.
- Grok CLI `1.0.46` (`2765805b9442`), `grok agent --always-approve stdio`.
- OpenCode `v2.0.23`, native `opencode acp`.

Per runtime: one disposable git consumer, seeded
`.kaola/heartbeat-prompt.json` (project, grants, `mode: node` Sideagent
binding `codex-KPR1035C-sideagent` on preset `codex/luna`, task
`qa-observe`, link `qa-prior-reclaim-1`), Host session
`<plat>-KPR1035C-orchestrator-main`. Trigger: one `/compact` prompt, the
same finite source-supported route as the 862 proofs. All runs used the
candidate `kaola-tmux.sh` and a lane-private `KAOLA_ACP_RECORD_ROOT`.

## 2. Results per runtime

### 2.1 Codex `0.160.1` — Host `c0c935cbaee999d195a44ab3b1d53af0`, session `01a11098-40c1-7723-8928-a32b882c4d09`

| Outcome | Result | Evidence |
|---|---|---|
| O1 negotiation | VERIFIED (candidate fix) | `initialize` sent `clientCapabilities.session.compaction={}` — event cursor 1, `receipts/02c-negotiation.json`. The installed holder omits this; the 862 run saw only a tool-call fallback. |
| O1 signal | VERIFIED | `session/update` `compaction_update` `status: "completed"`, `compactionId 01a1109b-29f7-7a40-8644-3830a2a601a6`, same sessionId → `compact_reload_detected` cursor 88, `role: host`. Usage `21798`→`6059` of `258400`. Route: explicit `/compact`. |
| O2 reread/use | NOT VERIFIED automatic; controller-assisted only | `compact_reload_native_owned` cursor 89 (correct bypass). The project hook was prepared and bound to this session and root (`binding.json` verified) but produced no effect: no `hooks.state` entry for the project `hooks.json` in `~/.codex/config.toml`, no payload text in the stream, and the next turn read `workflow-next/SKILL.md` (9772 B, byte+last-line verified) — not the `~/.codex/skills/kaola-project-runner` the hook names. Measured: codex-acp `runCompact` on `0.160.1` does not fire `SessionStart(compact)`. |
| O3 Host chain | VERIFIED as chain; checkpoint partial | `host_compact_maintenance_registered` cursor 92 → `recovery#1` (kind `host-compaction`, source `completed-host-signal`, occurrence-bound, evidence `events.jsonl#88`). Automatic node start cursor 93, recovery-only batch `b-90965c51ce82` cursor 94 (host_revision 3→3). Node checkpoint settled at 346: source-bound `checked` lists for all three scopes, but `verified: false`, `settled: []`, `returned_to_host {"recovery#1": "recovery-entry-unknown"}` → `checkpoint-partial` recorded (350) plus `maintenance-returned` alert. `recovery#1` stays a Host obligation. Exact stop 353 (`e1f8fbd3`, `stopped: true`). |

Business node cycle 1 also completed: `b-c67d090d12cc`, verified
checkpoint through revision 3, node `daf020e8` exact-stopped (83).

### 2.2 Grok CLI `1.0.46` — Host `5aba1ef376add2009ceafba68944d111`, session `01a110a7-0bcd-71b1-9b6e-06045627b3a3`

| Outcome | Result | Evidence |
|---|---|---|
| O1 signal | VERIFIED | `_x.ai/session_notification` `auto_compact_completed`, session-bound, `compact_reload_detected` cursor 136, `role: host`, source `grok-auto-compact-completed`. Route: `/compact`. Note: `tokens_before == tokens_after == 21219` (degenerate fields recorded as observed; the session-bound completed event is the proof, not tokens). |
| O2 reread/use | VERIFIED, automatic | `compact_reload_delivered` cursor 143 (prompt fingerprint `bf48d26d`). The reload turn ran `read_file` on `qa/progress.md` (303), `qa/task-skill.md` (307), `~/.grok/skills/kaola-project-runner/SKILL.md` (311), `~/.grok/skills/grok-kaola-project-runner/SKILL.md` (315). Continuation appended `progress.md`: `17407 B` / `10193 B` with last lines — both verified byte-for-byte against the installed files. |
| O3 Host chain | VERIFIED as chain; checkpoint partial | `recovery#1` registered cursor 146 (evidence `events.jsonl#136`). Automatic node start + batch `b-a3222b0e394e`. Checkpoint: `verified: false`, `settled: []`, `returned_to_host {"recovery#1": "recovery-entry-unknown"}`; `checkpoint-partial` alert recorded. Exact stop 1384 (`030c3132`, `stopped: true`). |

Business node cycle 1 verified (`b-c869920e8b25`, node `427992be`,
stopped 131). Prior evidence preserved: occurrence 878 and the
controller-assisted read/use stay on record; this run adds the missing
automatic Host-duty → node → checkpoint → reclaim seam.

### 2.3 OpenCode `v2.0.23` — Host `a1d1be782e600b94b9f191ab23dd3617`, session `ses_eef4a6639ffe1ZS1KQz2TX15LH`

| Outcome | Result | Evidence |
|---|---|---|
| O1 signal | VERIFIED | `session_info_update` `_meta["opencode/compaction"]` `status: "completed"`, `reason: "manual"`, `messageId msg_110bb50a7001n2hTSSm3OoFdCQ`, session-bound → `compact_reload_detected` cursor 33, `role: host`, `occurrence_id` = messageId. Closes the 862 gap “the installed holder emitted no compact_reload event” on the candidate. |
| O2 reread/use | VERIFIED, automatic | `compact_reload_delivered` cursor 35. The reload turn pulled the installed Skills as `skill_content` (`kaola-project-runner` cursor 50, `opencode-kaola-project-runner` cursor 93), then appended `progress.md` with `qa/task-skill.md` 204 B, `kaola-project-runner` 17407 B, `opencode-kaola-project-runner` 10597 B, last lines verified against installed files. |
| O3 Host chain | VERIFIED as chain; checkpoint partial | `recovery#1` registered cursor 36 (evidence `events.jsonl#33`). Automatic node start + batch `b-a2f62de87573`. Checkpoint: `verified: false`, `settled: []`, `returned_to_host {"recovery#1": "recovery-entry-unknown"}`; `checkpoint-partial` alert recorded. Exact stop 152 (`2b57e8c0`, `stopped: true`). |

Business node cycle 1 verified (`b-aa44359a20e2`, node `d1643d3e`,
stopped 30). Prior occurrence 36 and the controller-assisted 2.0.23
read/use stay valid; this run adds the missing automatic Host chain.

## 3. Cross-cutting measured findings

1. The candidate negotiation fix works on Codex. With
   `clientCapabilities.session.compaction={}` sent, the adapter emits the
   structured `compaction_update` `completed`; the installed holder (no
   capability) had none in the 862 record.
2. The Host seam executes end-to-end on all three runtimes: real
   session-bound completed signal → `compact_reload_detected` → typed
   `recovery#1` → automatic node start at a safe boundary →
   recovery-only batch → source-bound checkpoint → exact holder stop.
3. Consistent partial result: all three recovery checkpoints returned
   `recovery-entry-unknown`. The strict contract allows only `input`,
   `checked`, `unavailable`, `applied` keys on a `recovery#N` entry; each
   node emitted an entry with an extra key, the validator refused the
   settle, the duty stayed open with a recorded `maintenance-returned`
   alert and a bounded-check next step. This is the designed degraded
   path exercised for real — not a detection failure.
4. Codex native-route gap (measured, not assumed): the hook files are
   correctly installed and bound, but `SessionStart(compact)` does not
   fire under codex-acp `2.0.1` `runCompact`. The designed Codex native
   reread path therefore had no automatic effect in this run.
5. Grok token fields are degenerate (`21219`→`21219`); recorded, not
   used as proof.
6. Codex version note: manifest requests `0.160.0`; the resolved
   installed binary is `0.160.1`.

## 4. Proposed capability-table values (contribution, not a matrix)

| Runtime (tested) | O1 real completed signal | O2 Skill reread/use | O3 Host duty→node→checkpoint→reclaim |
|---|---|---|---|
| Codex `0.160.1` / codex-acp `2.0.1` | YES — `compaction_update` completed, session+host-bound; candidate negotiation verified (explicit `/compact` route) | NO automatic — native `SessionStart(compact)` hook not fired over ACP; controller-assisted read only | YES chain — auto node + source-bound checkpoint; checkpoint `partial` (`recovery-entry-unknown`), duty retained, exact reclaim |
| Grok CLI `1.0.46` | YES — `auto_compact_completed`, session+host-bound (explicit `/compact`) | YES automatic — holder-delivered reload, full installed reads byte-verified, continuation recorded | YES chain — same partial checkpoint result, exact reclaim |
| OpenCode `v2.0.23` | YES — `opencode/compaction` `completed` manual, session+host-bound (explicit `/compact`) | YES automatic — installed Skills reread byte-verified, continuation recorded | YES chain — same partial checkpoint result, exact reclaim |

Not claimed: automatic native reread on Codex; a fully settled
`recovery#N` checkpoint (all three were `partial`); spontaneous
limit-triggered compaction on any runtime (only the explicit `/compact`
route was exercised).

## 5. Limitations and unreached facts

- `/compact` is an explicit command route. Compaction triggered by a real
  context-limit event was not reproduced in finite scope.
- Whether a node can produce a contract-valid `recovery#N` entry is
  unmeasured: every node added a key the validator refuses. Business
  batches verify cleanly; recovery entries hit the strict rule.
- Codex: the hook is proven installed and bound only; firing needs a real
  `SessionStart(compact)` event the ACP path did not produce.
- A first Codex attempt was contaminated (a driver bug left an earlier
  Host alive; two Hosts shared one record dir and produced
  `host-identity-required` refusals and a premature `node_lost`). That
  attempt was stopped, all its processes killed, its records removed, and
  the run repeated clean. All quoted results come from the clean run.

## 6. Cleanup

All three Hosts and all six node holders were exact-stopped by identity
(`09-host-stop.json` receipts, `sideagent_node_stopped` events,
`holder-unreachable` final states). `residuals: []` in every run
receipt; a final `pgrep KPR1035C` sweep returns nothing. No repository,
installed-Skill, global-config, native-account, or consumer-project writes
occurred; only `core/**` was written.

## 7. Receipt index (per runtime, under `core/<plat>/receipts/`)

- `seed-0*.json` fixture seeds; `01-host-start.json`; `02-host-state.json`;
  `02c-negotiation.json` (initialize frame + agent caps); Codex only
  `seed-04-hook-prepare.json`, `02b-hook-bind.json`.
- `03-setup-send.json`, `04-setup-turn.json`, `node-cycle-business-1.json`,
  `events-after-node1.json`.
- `04b-pre-compact-quiet.json`, `05-compact-send.json` (+`05b`),
  `06-compact-signal.json`, `07-recovery-registration.json`,
  `08-reload-outcome.json` (+`08b/08c/08d`), `events-post-compact.json`.
- `node-cycle-recovery-2.json`, `node-events-all.json`,
  `final-heartbeat-prompt.json`, `09-host-stop.json`,
  `receipt.json` (per-run summary incl. residual check), plus
  `core/*/run/records/**` original event logs. Node exact-stops are the
  `sideagent_node_stopped` events in those logs (holder-automatic reclaim);
  there is no separate node-stop receipt file.
