# Issue 264 edge lane delivery r2 — Kimi/ZCode/Devin (same assignment, same holder)

Lane `/tmp/kpr-i264-host-chain-1035/edge`. Date 2026-10-06. This revision
answers the Host continuation and the checkpoint causal correction. The r1
report is preserved unchanged at `delivery-r1.md`; r1 raw outcomes stand.
Candidate and route are unchanged: frozen `4b247a2d`, checkout invocation,
scrubbed inherited binding env, per-bundle `KAOLA_ACP_RECORD_ROOT`. No
repository, installed, global, or consumer write outside `edge/**`.

## 1. Verdict

ZCode positive stands with corrected provenance. Kimi and Devin positives are
NOT yet obtained, after genuine finite attempts on fresh fully-linked
consumers. The blocking cause for Kimi is now confirmed and reproduced: the
maintenance node writes an invalid recovery entry (extra `retained` plus a
`checked`/`unavailable` scope overlap), which the state tool correctly rejects
as `recovery-entry-unknown` before any missing-originals logic. Devin's second
consumer additionally hit two `old-node-live` selection races and very long
Host wake turns; its recovery batch was still undelivered at the bounded close.
Exact causal evidence, a smallest proposed guidance correction, and next
recovery are below. All raw negatives are preserved; none was altered.

## 2. Causal correction accepted and verified (Host checkpoint correction 1059)

I re-parsed the original node `state checkpoint` commands from the node session
event logs. The Host's parse is correct:

- kimi node cursor 1182 (`kimi/records/codex/codex-KPR103EK-sideagent/
  <dir>/events.jsonl`): recovery#1 entry = `{"input", "retained":
  "tasks/qa-observe", "checked":{authorization,duties,links},
  "unavailable":{"links": ...}}`. Extra `retained` key → rejected
  `recovery-entry-unknown` (dispatch 4b247a2d `checkpoint_entry` 4794-4814,
  key check before scopes). `checked.links` and `unavailable.links` also
  overlap (a second violation had the key check passed). The
  `recovery-originals-unavailable` path was never reached.
- devin node cursor 1452 (`devin/records/codex/codex-KPR103ED-sideagent/...`):
  same shape, extra `retained":"tasks/qa-observe"`, same overlap, same cause.
- zcode node cursor 1401 (`zcode/records/codex/codex-KPR103EZ-sideagent/...`):
  recovery#1 entry = `{"input","checked":{...}}` only — valid; the `seq` in the
  normalized result is tool-added provenance (dispatch 4934-4937), not an input
  key. This entry is what verified recovery#1 in batch `b-0adc9f467511`.

Correction to r1: r1 said the Kimi/Devin partials were "by design … links
unavailable because of the seeded gap". That was wrong. The true cause is the
invalid entry shape written by the node. The seeded gap influenced the node's
`unavailable.links` text (and plausibly the merged bookkeeping), but the gap's
own refusal path was not the operative reason. r1's negative outcomes, event
cursors, and receipts remain accurate as raw facts.

## 3. ZCode provenance correction (manual probes named; automatic start proven)

Three receipts in `zcode/receipts/` were written by the ZCode Host model during
its own wake turns (not by this controller; timestamps UTC):

1. `host-stop-sideagent.json` 09:57:54 — model ran `codex stop` for
   `codex-KPR103EZ-sideagent`; result `no-session` (no record in the default
   record root; the lane used `KAOLA_ACP_RECORD_ROOT`). Failed manual probe.
2. `host-start-sideagent-recovery.json` 10:06:14 — model ran a manual
   `codex start`; refused `heartbeat-host-unresolved`, `mutation_status:
   not_started`. Failed manual probe.
3. `host-start-sideagent-chain3.json` 10:17:49 — same refusal, `not_started`.
   Failed manual probe (this one landed after the automatic node had already
   started).

Why the model ended the binding: during its first wake turn it saw the batch-1
node's stopped record (09:50:54Z, holder `9394fe7e…`) and its own failed
no-session stop probe, and wrote `state.sideagent.state=ended` citing exactly
those sources (binding `source` field names `record.json state=stopped` and
`receipts/host-stop-sideagent.json`). It treated the normal per-batch node stop
as the end of the sideagent lifecycle. That is a Host model judgment, not a
carrier defect.

Controller re-activation: `zcode/receipts/state-reactivate.json` 10:13:17
(`state update --section sideagent`, file rev 15, host_revision 10, source
names the edge-lane controller; `since` refreshed so the failed-start flag
cleared). This was controller-assisted setup, not automatic Host repair, and
r1 already labels it so; the automatic chain parts remain: signal → duty →
node start → batch → settle → stop.

Proof the automatic holder `11ab6bbf…` came solely from the carrier: (a) host
event 3594 `sideagent_node_started` was written by the Host holder itself for
its `_start_node` recipe subprocess at 10:15:09Z, 4 s after duty registration
(3593 at 10:15:05.86Z); (b) both manual start attempts ended `not_started`
with no holder id and created no record; (c) the running node's record lives
under the lane record root (`zcode/records/codex/codex-KPR103EZ-sideagent/
af6ada8b4fad8173/`), which the model's attempts never referenced — they
consulted the default root and found nothing; (d) the latest manual attempt
(10:17:49) postdates the automatic start and also failed. No further manual
start was attempted by the controller.

## 4. Post-compaction reread exposure — exact limits preserved

Same-session reload-turn reads, per runtime (files, then exposure):

- Kimi (reload turn cursors 727–2423): tool result chunks at 1903 and 1904
  carry the FULL numbered payloads — 1903 `1\t---\n2\tname:
  kimi-cli-kaola-project-runner…` (11,205 chars in the recorded chunk) for
  `~/.agents/skills/kimi-cli-kaola-project-runner/SKILL.md` (10,260 B, 165
  lines, sha256 `90f1c257…`, unchanged from 652); 1904 for
  `~/.zcode/skills/kaola-project-runner/SKILL.md` (17,407 B, 264 lines,
  sha256 `1af732f3…`; 18,956 chars). Raw ACP does carry the full bytes here.
- ZCode (reload turn 3592–4499): 3703 and 3708 are completed Read tool calls
  with `rawInput {"file_path": …}` only — no offset/limit (source support for
  a no-limit read) and NO content payload in the event stream. The bridge does
  not stream read bodies. Byte/end-line semantics for these exact files come
  from the same session's setup-turn records in `qa/progress.md` (10029 B /
  163 lines platform skill `3e0da3e1…`; 17407 B / 264 lines main skill) and
  from the accepted unchanged 673 proof (fresh full Read, all nonblank lines).
  The raw ACP stream does not contain the bytes; that limit stands.
- Devin (reload turn 271–896): 375 and 377 expose ONLY `"165 lines"` and
  `"264 lines"` summaries (devin platform skill 10,438 B `061c707d…`; main
  skill 17,407 B). Full-body reread evidence for Devin remains the accepted
  873 manual re-invocation route; today's ACP exposure is summary-only.
- Continuation distinction: kimi's reload turn appended distinct TASK-B
  post-compaction lines to `qa/progress.md` (separate from its TASK-A setup
  lines); devin's continuation is its reconcile beat (state task rev 4, alert
  kept open, node partial recorded); zcode's setup lines stand and its
  post-compact continuation is carried by the recovery batch itself.

No native rerun was made to print bytes; unchanged prior stage proof is reused.

## 5. Claude — bounded delta and boundary reasoning (no new run)

Between the 055-proof candidate `0553a8db` and frozen `4b247a2d`:

- `scripts/kaola-compact-recovery.py` and `scripts/kaola-zcode-acp.py`:
  byte-identical (c45662a4…, 35815c83…). `vendor/claude-code-acp/dist/index.js`
  (2135ad71…), `scripts/adapters/claude-code.sh`, and `scripts/claude-code-tmux.sh`
  are not in the diff — the Claude transport seam is unchanged.
- `scripts/kaola-acp-holder.py` +18 lines, three hunks only: (1)/(2)
  own-session gating for `usage_update` context and projection; (3) the
  maintenance-node prompt text (`applied`/`retired:` semantics, single
  checkpoint, no replayed checkpoint). The compaction functions
  (`_observe_compact_signal`, `_register_compact_maintenance`,
  `_deliver_compact_reload`) are untouched.
- `scripts/kaola-dispatch.py` (+568/−183) and `scripts/kaola-record-contract.py`
  (+519) changed the state tool and schema surface; `kaola-acp.py` (+235) and a
  new launchd broker are outside the compaction chain.

Boundary reasoning: the 055 full-chain proof stays an old-candidate
(`0553a8db`) proof of holder `4ae5543d…`/dispatch `71357f28…`. The changed
current bytes were exercised live on this assignment by three Host seams
(kimi/zcode/devin: signal→register→reload→auto node→settle→stop, one verified
checkpoint) plus two more consumers in §6, so the changed common mechanism has
current-runtime coverage — but that is not a fresh Claude execution, and no
Claude seam is invalidated by the three holder hunks (two are usage-update
scoping; one is node prompt text, already live-covered). Source-only reasoning
and any affected review stay with the Host. Pins: `common/candidate-pins.txt`;
original dated proof: `/tmp/kpr-i264-929-host-proof-verification.json`,
`/tmp/kpr-i264-882-host-proof.md`.

## 6. Positive counterparts — finite attempts and truthful results

### 6.1 Kimi (`kimi2`, fully-linked fixture, no `qa-gap-missing`)

- Consumer `kimi2/repo`; dispatch list `["qa-prior-reclaim-1"]` only; AGENTS.md
  requirement 3 replaced with the fully-linked rule; all workflow/ledger
  originals present from the start. Builder `common/build-lane2.sh`.
- Host start receipt `kimi2/receipts/host-start.json`: holder `460bc03b…`,
  ACP `session_e7c97c86…`, `session_role: host`, native selection
  `kimi-code/k3` thinking `max` (declared default).
- Batch 1 `b-67e4eb137e58` through=3: checkpoint verified @1270, node
  `a3ec3c0c…` stopped @1275.
- Native compaction: real marker at 8759 — `Compaction completed.
  - Messages compacted: 31
  - Tokens before: 49,777
  - Tokens after: 31,857` — detected `kimi-compaction-chunk`, role host, own
  session; duty @8761 (recovery_seq 1, host_revision 3 unchanged); reload
  delivered @8760; reload turn ended @15386; automatic node `8095a734…` @15387;
  recovery batch `b-3457f6b9666b` @15388.
- Result: checkpoint PARTIAL again — returned `recovery#1:
  recovery-entry-unknown`. The node's command shows the recovery entry again
  carrying `"retained":"decisions/qa-prior-reclaim-1"` (and the same
  checked/unavailable links overlap). Second independent reproduction on a
  fully-linked fixture: the fixture gap is NOT the cause; the node-entry
  construction is. Settled @15389, alert @15392, node stopped @15395, Host
  exact-stop exit 0, residuals [].
- Conclusion: Kimi positive NOT obtained after two genuine attempts (r1 kimi,
  kimi2). Finite exhaustion recorded; the confirmed cause and the one-sentence
  guidance correction are in `common/proposed-node-prompt-correction.txt`.
  Positive verification for the Kimi seam waits on that correction (or a node
  run that happens to write a clean entry); the detection→duty→auto-node→
  reclaim chain itself is proven twice on this seam.

### 6.2 Devin (`devin2`, fully-linked fixture, real Host decisions)

- Consumer `devin2/repo`, same fully-linked shape. Host holder `0af69242…`,
  ACP `rocky-citrus`, native selection `swe-2-max` (default tier).
- Batch 1 `b-41a3dda4633f` verified @438, node `5f70eaf9…` stopped @447.
- Real Host business writes from Host turns (not controller writes): pending
  decision `qa-task-a-verdict` rev 4 (the Host first refused my settled-on-create
  payload with `record-missing` and proposed the pending route itself — receipt
  `host-send-decision.json` + its reply), rev 5 wake write, pending decision
  `qa-compact-readiness` rev 7 (`host-send-decision3/4.json`).
- Two `old-node-live` selection races: @1601 (batch:5) and @3851 (batch:7).
  Each left a started node without a carrier batch (`dd6071bc`, `47d7c688`);
  `stop_confirmed_late` @2749 self-healed the first. The second node
  (`47d7c688`) stayed alive batchless and wrote an out-of-band, self-named
  checkpoint (`b-47d7c688dfcd-r7`); the contract correctly returned
  `batch:7 not-in-batch`. This is preserved negative evidence of the contract
  holding, and a recorded observation for the sole writer (inspection request
  in the correction file; no patch proposed on two occurrences).
- Native compaction (after two `prompt-in-progress` refusals during wake turns,
  both undelivered and safely retried at idle boundaries): `started` @4956,
  `completed` @4957, detected @4958 (`devin-compaction`, role host, own
  session), reload @4959, duty @4961 (recovery_seq 1, revision 8 unchanged at
  registration).
- Bounded close: the reload turn ran ~18 min (ended @6015); the following
  partial-checkpoint wake turn was still active after ~25 more minutes. The
  recovery batch had not been delivered when I exact-stopped the Host
  (`devin2/receipts/host-stop.json`: exit 0, residuals [], the stop swept the
  batchless node's process group 27987; node record state stopped, pid dead).
  `recovery#1` remains pending in the preserved state file — the lane is
  recoverable by resuming at an idle boundary or rerunning a fresh consumer.
- Conclusion: Devin positive NOT obtained in this window. Not a support claim;
  the chain reached duty registration twice (r1 delivered a full partial
  checkpoint; r2 reached duty) and the remaining distance is the recovery
  batch delivery + one clean node entry.

### 6.3 What would have been invalid, and was not done

No old partial was edited into a verified one; no controller-started node (the
kimi2/devin2 nodes were all carrier-started; the only controller node-related
action remains the labeled zcode binding re-activation); no hand-written
checkpoint; no schema or product byte changed; no business-only verified
checkpoint was offered as recovery settlement (kimi2 batch-1 verified
checkpoints settle business only; recovery#1 stayed open there).

## 7. Updated row contributions (Host matrix; no repository write)

- Kimi CLI 2.1.1 + candidate `4b247a2d`: outcomes 1/2 reused (652). Outcome 3:
  detection→duty→auto-node→exact-reclaim PROVEN twice (r1 cursors 726–2435;
  r2 8759–15395). Verified recovery checkpoint NOT yet obtained — node writes
  an invalid recovery entry (extra `retained`, scope overlap) on recovery-only
  batches; reproduced twice; guidance correction proposed. Route explicit
  `/compact`; chain automatic.
- ZCode 0.16.9 + candidate bridge `35815c83…`: as r1, with corrected
  provenance: three failed manual model probes named (no-session stop; 2×
  heartbeat-host-unresolved starts); automatic `11ab6bbf` proven carrier-only;
  controller binding re-activation labeled setup assistance. Verified batch
  `b-0adc9f467511` stands.
- Devin 3000.11.3 + candidate `4b247a2d`: outcomes 1/2 reused (873). Outcome
  3: r1 delivered duty→auto-node→partial(invalid-entry)→wake→reclaim; r2
  reached duty (4958/4961) with a fully-linked fixture and real Host business,
  but the recovery batch was undelivered at the bounded close (long wake turns;
  two `old-node-live` races). Positive pending; exact recovery next step named
  in §6.2.

## 8. Cleanup

- New stop receipts: `kimi2/receipts/host-stop.json`, `devin2/receipts/
  host-stop.json` (both `stopped:true`, exit 0, `residual_pids:[]`; the devin2
  stop additionally swept the batchless node pgid). All node records across
  kimi2/devin2 show state stopped; pids dead; `pgrep KPR103E` returns none.
- Nothing outside `edge/**` written; no install/login/timer/framework; the
  live KPR Host, its node, other lanes, and this lane's own dispatched session
  were not contacted or controlled.

## 9. Known limits

- Automatic background compaction (no `/compact`) remains unmeasured on all
  three runtimes; only the explicit route was exercised.
- The Kimi verified-recovery positive is blocked by a reproduced node-entry
  defect, not by the Kimi seam; adoption of the one-sentence prompt correction
  is the Host's decision, with a one-run affected proof proposed.
- Devin r2 is a bounded close, not an exhaustion of the platform: the recovery
  batch delivery remains a concrete next step; `recovery#1` stays pending in
  the preserved consumer state.
- ZCode/Claude were not rerun; reuse claims and the bounded Claude delta are
  in §4/§5.
