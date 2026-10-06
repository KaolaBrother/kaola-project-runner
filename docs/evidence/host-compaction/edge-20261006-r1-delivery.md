# Issue 264 edge lane delivery — Kimi CLI, ZCode, Devin Host-compaction chain

Lane: `/tmp/kpr-i264-host-chain-1035/edge` (Kimi/ZCode/Devin; Claude read-only reuse).
Date: 2026-10-06. Worker-class diagnostic only. No claim, no ledger of record, no
product write, no acceptance authority. Workflow OFF for this lane.

## 1. Verdict

PROVEN on the frozen candidate `4b247a2dbae9006be71962da32b31e5c5eb05629`: on all
three assigned runtimes, one real, explicit, session-bound native compaction
`completed` signal on a Host-role ACP session created the typed recovery duty
without any Host request or business write, the carrier automatically started the
bound Sideagent node at the next safe boundary, the node produced a
holder/batch/source-bound scoped checkpoint, and every node and Host was
exact-stopped with receipt. ZCode produced one fully `verified` recovery
checkpoint. Kimi and Devin produced honest `partial` checkpoints: the seeded
`qa-gap-missing` link gap has no original, so the `links` scope was returned, not
faked. This is the designed no-PASS path. All raw events, prompts, receipts, and
state files are preserved under this lane.

## 2. Measured object and route

- Candidate: frozen worktree `.kw/worktrees/issue-259` HEAD `4b247a2d`, exported
  with `git archive` to `edge/candidate` (clean export; no `.git`).
  Pins: `common/candidate-pins.txt`. Key hashes (sha256):
  - `scripts/kaola-acp-holder.py` `d8cc9dc1…b72f280` (differs from the 055-proof
    bytes `4ae5543d…`; see §6)
  - `scripts/kaola-dispatch.py` `140d1399…c6fbfd` (055 proof had `71357f28…`)
  - `scripts/kaola-compact-recovery.py` `c45662a4…e90f27` (byte-identical to the
    accepted 055/929 verification)
  - `scripts/kaola-zcode-acp.py` `35815c83…99ecadd` (identical to the 673 proof)
- Invocation route: direct checkout `candidate/scripts/kaola-tmux.sh <platform>
  start/send/stop` (the documented diagnostic no-install path;
  `baseline_exempt: true` in every start receipt; no installed activation).
- Installed Skills used at dispatch (current, read-only):
  - Kimi: `~/.agents/skills/kimi-cli-kaola-project-runner/SKILL.md` 10260 B,
    sha256 `90f1c257…66479e` — identical to the accepted 652 read.
  - ZCode: `~/.zcode/skills/zcode-kaola-project-runner/SKILL.md` 10029 B, sha256
    `3e0da3e1…`; main `kaola-project-runner` 17407 B, sha256 `1af732f3…`.
  - Devin: `~/.config/devin/skills/devin-kaola-project-runner/SKILL.md` 10438 B,
    sha256 `061c707d…ea533` — identical to the accepted 873 read.
- Runtimes: Kimi CLI 2.1.1 (`kimi acp`, declared default k3/thinking=max);
  ZCode app-server 0.16.9 through candidate bridge `kaola-zcode-acp.py`
  (GLM-5.3/thought=max, the #108 Host gate); Devin CLI 3000.11.3
  (`devin acp --model swe-2-max`, default tier); codex-cli 0.160.1 as the bound
  maintenance node (`codex/luna`, `--role sideagent` — the 055-proven node
  recipe; the runtime-specific seam under test was the Host).
- Every child launch scrubbed the inherited worker-binding env
  (`KAOLA_ACP_DISPATCHER`, heartbeat host vars, `KAOLA_ACP_CHILD_RECORD`,
  provider-config injections). Records were isolated per bundle through
  `KAOLA_ACP_RECORD_ROOT=edge/<rt>/records`.
- Fixture per runtime (disposable git consumer `edge/<rt>/repo`): AGENTS.md owner
  block, `qa/progress.md`, `.kaola/delegator-heartbeat.json`,
  `.kaola/dispatch-index.json` (item `qa-prior-reclaim-1` points at the runtime's
  real accepted prior receipts; `qa-gap-missing` stays a deliberate row-less
  dispatch ref), lifecycle state seeded only with the candidate state tool
  (`state init` + `state update --section sideagent` + tasks; host_revision 3),
  and fixture-labeled `kaola-workflow/kaola-project-runner/workflow-state.md` plus
  `kaola-workflow/.ledger/issue-264.jsonl` present from the start (055 lesson).

## 3. Per-runtime chain results

Cursor numbers refer to each Host `events.jsonl`. Summaries with raw signals:
`<rt>/receipts/chain3-summary.json`.

| Step | Kimi CLI 2.1.1 | ZCode 0.16.9 (candidate bridge) | Devin 3000.11.3 |
|---|---|---|---|
| Host session / holder / ACP id | `kimi-cli-KPR103EK-orchestrator-main` / `8043c539…` / `session_58ad0c33…` | `zcode-KPR103EZ-orchestrator-main` / `eaa5f0c6…` / `zcode-1` | `devin-KPR103ED-orchestrator-main` / `d72ff0e5…` / `gelatinous-comma` |
| Start receipt | `kimi/receipts/host-start.json` (`session_role: host`) | `zcode/receipts/host-start.json` | `devin/receipts/host-start.json` |
| Pre-compaction batch 1 (seeded revisions) | batch `b-32e343bcede5` through=3, checkpoint **verified**, node `f48dcede…` stopped @722 | batch `b-318d92597beb` through=3, **verified**, node `9394fe7e…` stopped @141 | batch `b-452c5a873916` through=3, **verified**, node `6719086d…` stopped @266 |
| Setup turn (bounded real reads of installed Skills) | ended @716; byte counts and last lines recorded in `qa/progress.md` (10260 B / 17407 B — match disk) | ended @135; recorded (10029 B / 17407 B) | ended @260; recorded (10438 B / 17407 B) |
| Trigger | prompt `/compact` (send receipt `host-send-compact.json`, fingerprint `sha256:52e657bd…`, same text on all three lanes) | same (second send; see §5) | same (turn ended in 2 ms, as in 873) |
| Native completed signal (outcome 1, explicit route) | `agent_message_chunk` text exactly `Compaction completed.\n- Messages compacted: 13\n- Tokens before: 33,117\n- Tokens after: 24,943` → detected @726 `source=kimi-compaction-chunk`, `role=host`, own session id | bridge-mapped `session/update` `compaction_update status=completed`, `compactionId=zcode-state-14` → detected @3591 `source=acp-compaction-update`, `role=host`, `session_id=zcode-1` | notification `_cognition.ai/compaction` `status=completed` with summary path (raw at cursors 268–270) → detected @270 `source=devin-compaction`, `role=host`, own session id |
| Recovery duty (outcome 3a) | `host_compact_maintenance_registered` @728: `recovery_input seq=1 kind=host-compaction source=completed-host-signal`, holder `8043c539…`, evidence `events.jsonl#726`; `host_revision` stayed 3 (no business edit) | @3593: same shape, occurrence `zcode-state-14`, evidence `#3591`; revisions stayed as written before the signal | @273: same shape, evidence `#270`; `host_revision` stayed 3 |
| Reload delivery (separate duty) | @727 `compact_reload_delivered` fingerprint `bf48d26d…` (Kimi host entry prefix) | @3592, same reload body family | @271, same |
| Automatic node at safe boundary (outcome 3b) | reload turn ended @2423 → node `ac407e74…` started @2424, batch `b-0d7be97b35b7` @2425 with recovery#1, through=3 (recovery-only selection: `handled == host_revision`) | node `11ab6bbf…` @3594; reload turn ended @4499 → batch `b-0adc9f467511` @4500 with recovery#1 + business revisions 4..10 (coalesced) | reload turn ended @896 → node `102735fe…` @897, batch `b-22f175756cbc` @898 with recovery#1, through=3 |
| Scoped checkpoint (outcome 3c) | settled @2426 `checkpoint=partial`: all three scopes checked against real originals (authorization 6 refs, duties 7, links 6); `recovery#1` returned `recovery-originals-unavailable` because the seeded `qa-gap-missing` has no original; alert `maintenance-returned` opened; Host woken @2428 | settled @4501 `checkpoint=verified`: `settled=[recovery#1, sideagent@10, tasks@7, alerts@9]`, `returned_to_host={}`, recovery `unavailable={}`, checked authorization 5 / duties 9 / links 9 real refs; `handled=acked=10` | settled @899 `partial` (same honest shape; links unavailable names `qa-gap-missing`); alert opened; Host woken @901 |
| Exact reclaim (outcome 3d) | node stopped @2435 receipt `{stopped:true}`; Host stop `kimi/receipts/host-stop.json`: exit 0, `residual_pids:[]` | node stopped @4506; Host stop `zcode/receipts/host-stop.json`: exit 0, residuals `[]` | node stopped @909; second node `9578b905…` (business batch @1625 after the Host's own rev-4 write) reclaimed by the Host stop; `devin/receipts/host-stop.json`: exit 0, residuals `[]` |

Delegator views: `<rt>/receipts/state-view-delegator.json`. All Host and node
record dirs under `<rt>/records/` keep full `events.jsonl` (including raw
signals), `record.json`, and children logs.

## 4. Real Host behavior after the partial checkpoints (not scripted)

- Kimi: the woken Host reconciled, wrote its own decision/state (rev 3→4), then
  ended the sideagent binding itself (`state=ended`, source names the node stop
  receipt). The carrier then refused a further node (`batch:4
  binding-or-recipe-unavailable` @7550) and surfaced it as a visible alert — the
  designed refusal, not a silent drop.
- Devin: the woken Host read the originals, refused a checkpoint write
  (`node-identity-required`, by design), refused to retire the alert while
  `recovery#1` was unsettled, and recorded the frontier in `tasks/qa-observe`
  (rev 4). Honest guardrails held.
- ZCode: the verified batch stayed quiet (`host_woken=false`); earlier business
  batches woke the Host and it reconciled at length (its turns wrote revisions
  4–10, which the recovery batch then settled in one verified checkpoint).

## 5. Failed attempts and safe retries (all preserved)

1. Kimi attempt 1 (`common/attempt-kimi-1/`): the recipe argv spelled the repo as
   `/tmp/…`; the holder canonicalizes to `/private/tmp/…`; the carrier refused
   the recipe (`sideagent_node_recipe_refused` @13, `binding-or-recipe-unavailable`
   @14) — the designed validation caught the fixture error. Host exact-stopped
   (exit 0), fixture corrected to canonical paths, run restarted. No repository
   write happened.
2. ZCode first `/compact` send: refused `prompt-in-progress` because the Host was
   inside its own wake turn (`zcode/receipts/host-send-compact.json`). One safe
   retry at an idle boundary after a labeled controller state write (see 3 below)
   succeeded (`host-send-compact2.json`). Effects reconciled from events before
   the retry; no replay of an unknown write.
3. ZCode binding re-activation (`zcode/receipts/state-reactivate.json`): the
   ZCode Host model had ended the binding during its reconciliation. The lane
   controller re-activated it (`state update --section sideagent`, file rev
   15, host_revision 10, source `qa-diagnostic:reactivate sideagent binding for
   compact chain-3 boundary (edge-lane controller)`) and refreshed `since` so the
   carrier's failed-start flag cleared. This was a controller-assisted fixture
   repair inside the disposable repo, recorded as such; it is not native Host
   behavior and is not counted as automatic activation.

## 6. Claude — read-only reuse (no repeat run)

- The immutable 055 proof stays accepted as-is: Claude Code 2.1.289, candidate
  `0553a8db`, bridge `2135ad71…`, holder `4ae5543d…`, dispatch `71357f28…`,
  native completed 41/42 → recovery input 43 before reload 46, installed Reads
  49/50 with byte/end-line checks 51, TASK-B 52, seven node lifetimes, verified
  final checkpoint `b-3364a45e5f1b` (`/tmp/kpr-i264-929-host-proof-verification.json`).
- Today the installed Claude Skills are byte-identical to what 055 read:
  `~/.claude/skills/kaola-project-runner/SKILL.md` 17407 B sha256 `1af732f3…`,
  `~/.claude/skills/claude-code-kaola-project-runner/SKILL.md` 10472 B sha256
  `68989e48…`. Nothing changed on the Claude seam, so no repeat is justified.
- Cross-candidate fact for the Host: between `0553a8db` and `4b247a2d`,
  `kaola-compact-recovery.py` and `kaola-zcode-acp.py` are byte-identical;
  `kaola-acp-holder.py` (+18 lines) and `kaola-dispatch.py` (+568/−183) changed.
  The three chains in §3 ran the changed bytes live, so the newer candidate's
  chain-3 mechanism now has one verified recovery checkpoint (ZCode) and two
  honest partial+recovery-loop chains (Kimi, Devin) in addition to 055's Claude
  proof of the older bytes.

## 7. Proposed table rows (for the ONE Host-maintained matrix; no repository write)

| Runtime / version | Outcome 1 (signal) | Outcome 2 (reread/use) | Outcome 3 (Host chain) | Route | Evidence | Limits / recovery |
|---|---|---|---|---|---|---|
| Kimi CLI 2.1.1 + candidate `4b247a2d` | PASS (reused 652; re-observed live @726) | PASS (reused 652, installed skill hash unchanged `90f1c257…`) | PASS scoped: duty @728 (no business edit, host_revision 3), auto node @2424, batch @2425, partial checkpoint by design (links gap), alert + Host wake, exact stops | explicit `/compact`; detection/registration/node automatic | `edge/kimi/receipts/chain3-summary.json`, events cursors 726–728, 2423–2435, 7550–7551 | Recovery checkpoint honest-partial only on this lane (seeded gap). Automatic background compaction occurrence not forced. Host ended the binding by its own judgment after the node stop; next node needs a Host/carrier binding change. |
| ZCode 0.16.9 (desktop app-server) + candidate bridge `35815c83…` | PASS (reused 673; re-observed live @3591 `compactionId=zcode-state-14`) | PASS (reused 673) | PASS full: duty @3593, auto node @3594, batch `b-0adc9f467511` @4500 (recovery#1 + business 4..10 coalesced), checkpoint **verified** @4501 (`returned={}`, `unavailable={}`), exact stop @4506 | explicit `/compact` mapped by the bridge to engine `session/compact`; chain automatic | `edge/zcode/receipts/chain3-summary.json`, events 3589–3594, 4499–4506 | `/compact` send can be refused `prompt-in-progress` while a wake turn runs; retry at an idle boundary. Binding re-activation on this lane was controller-assisted (labeled receipt `state-reactivate.json`). |
| Devin 3000.11.3 + candidate `4b247a2d` | PASS (reused 873 manual route; re-observed live @270 `_cognition.ai/compaction completed` with summary path) | PASS (reused 873 manual re-invocation; installed skill hash unchanged `061c707d…`) | PASS scoped: duty @273, auto node @897, batch `b-22f175756cbc` @898, partial checkpoint (links gap), alert + Host wake, Host's own honest reconciliation (refused checkpoint write; refused alert retire while recovery#1 unsettled), exact stops | explicit `/compact` advertised command; chain automatic | `edge/devin/receipts/chain3-summary.json`, events 267–273, 896–909, 1622–1625 | Same links-gap qualification. Post-compact unsent-turn Skill carriage qualification from 873 still applies. Background auto-compaction unmeasured. |

Common qualification, all three rows: the maintenance registration receipt can
land one event cursor after `compact_reload_delivered` (the register call is
issued before delivery; its thread completes after). On 055 it landed before.
The duty stays bound to its signal cursor either way.

## 8. Cleanup and custody

- All six disposable holders (3 Host, 3 latest nodes) show `state=stopped`;
  every recorded pid is dead; `pgrep KPR103EK|KPR103EZ|KPR103ED` returns none.
- Stop receipts: `<rt>/receipts/host-stop.json` (each `stopped:true`,
  `agent_exit_code:0`, `residual_pids:[]`), plus `common/attempt-kimi-1/` for the
  refused-recipe attempt. Earlier node stops are confirmed in each Host events
  log (722 / 141,266 / 909) and node records.
- Nothing outside `edge/**` was written. No repository, source, generated,
  installed, global-config, or consumer-project write. The live KPR Host, its
  bound node, and other lanes were never contacted. This lane's own dispatched
  session (`zcode-KPR-i264-host-chain-edge`) was never controlled.
- No login, install, model/tier switch, timer, or new framework. Trigger routes
  were the already-accepted explicit `/compact` routes; no context flood.

## 9. Remaining limits and next recovery

- Automatic background compaction (no `/compact`) stays unmeasured on all three
  runtimes; only the explicit trigger was exercised. The classifier accepts any
  completed signal, but that is source fact, not a measured background occurrence.
- The Kimi and Devin `partial` checkpoints are honest returns, not defects: a
  seeded row-less dispatch ref has no original, and the state tool refuses to
  verify a recovery with an unavailable scope. To see a verified recovery on
  those two seams, seed a fully-linked dispatch index (no deliberate gap) or let
  the Host resolve `qa-gap-missing` first.
- One verified recovery checkpoint per Host seam is now proven for ZCode and
  (on older bytes) Claude; Kimi/Devin have duty→node→checkpoint→reclaim plus the
  Host recovery loop. If the owner wants verified checkpoints on those two seams
  too, rerun §3 with the gap removed; the fixture builder is
  `edge/common/build-lane.sh` under this lane.
- Smallest next check for the integrator: none required for the chain itself.
  Optional doc line: the `prompt-in-progress` refusal on a busy Host turn is a
  documented safe boundary for the compact trigger on ZCode (retry at idle).
