# Issue 264 edge lane delivery r3 — fixed-candidate positive counterparts

Lane `/tmp/kpr-i264-host-chain-1035/edge`, same holder assignment (Kimi/ZCode/
Devin; Claude read-only). Date 2026-10-06 (UTC timestamps below). r1/r2 and
every prior consumer are preserved unchanged. Workflow OFF; no claim, no
finalize; writes only under `edge/**`.

## 1. Verdict

On the exact fixed candidate `24a2355a226fc371b6502ea6b254b2157da6efa6`
(`edge/src-r3`, exported from the canonical `.kw/worktrees/issue-264` Git
object; the docs-only `644a383f` was NOT used), one finite fresh fully-linked
consumer per remaining seam was run:

- **Kimi CLI 2.1.1 — POSITIVE OBTAINED.** Full automatic chain: own-session
  native completed signal → automatic reload → independent typed duty →
  carrier-started fresh node → original-source-scoped checkpoint **VERIFIED**
  (`b-e93d1a2aaa85`, recovery#1 settled, `unavailable:{}`, three scopes
  checked) → exact node reclaim and Host stop, exit 0.
- **Devin 3000.11.3 — chain complete, checkpoint honestly PARTIAL.** Same
  automatic chain end-to-end with a now-VALID recovery entry (the guidance fix
  held; no `retained`, scopes split correctly). The node returned
  `recovery-originals-unavailable` on `links`: it requires a local Runner
  record for the seeded `devin-KPR103ED3-prior-diagnostic` session, which the
  fixture does not carry (its real prior receipts are /tmp files the node read
  and cited). This is a precise, source-supported remaining fixture-evidence
  limitation, not a mechanism gap and not an invalid-entry failure.

## 2. Provenance corrections (r3; verified against originals)

Accepted from the Host review and confirmed by my own re-parse:

1. **Kimi2 node command 1307** (raw in `kimi2/records/codex/
   codex-KPR103EK2-sideagent/…/events.jsonl`): the recovery#1 entry carried
   `input` + extra `retained:"decisions/qa-prior-reclaim-1"` + `checked`
   scopes. It had **no `unavailable` scope and no checked/unavailable
   overlap**. Only the `retained` defect reproduced there. My r2 statement
   repeating the first run's overlap into the second run was wrong.
2. **Devin2 later nodes were Host-model actions, not carrier races.** The full
   Host raw shows only ONE carrier node start (cursor 17, node `5f70eaf9`,
   batch 18, verified 438, reclaim 447). The later nodes and self-named
   checkpoints came from native Host-model tool commands: 1113
   `kaola-tmux.sh codex drain-restart --continue`, 2776 manual
   `codex start --continue`, 2860 direct send of a self-named
   maintenance/checkpoint assignment, and 3361 retiring a warning using that
   assisted result (originals: `/tmp/kpr-1069-devin-r2-manual-node-originals.json`).
   Those actions violated the fixture's finite no-session-control scope; the
   resulting checkpoints are excluded from automatic proof. The two
   `old-node-live` refusals saw live holders outside the carrier-owned holder
   and do NOT establish a carrier start race; my r2 "record race" wording is
   withdrawn. Controller actions in that lane (state writes, prompts, stops)
   remain as recorded in r2 §6.2 and are distinct from these model actions.
3. **Devin2 node `47d7c688` record is STALE.** Its latest record shows
   `ready`, but holder pid 27987 and agent pid 27988 are dead (Host stop swept
   27987). r2's "all node records show state stopped" claim is corrected:
   process/stop evidence is authoritative, the stale record is an observation.

## 3. Measured object and route (src-r3)

- Export: `git archive 24a2355a…` from `.kw/worktrees/issue-264` (worktree
  clean at export; object verified `commit` before export). Pins with UTC
  date: `common/src-r3-pins.txt` (exported 2026-10-06T12:41:21Z):
  holder `f455cd27…a1aa56`, dispatch `f80610b2…c566d`, launchd broker
  `c39e6894…3fe3a68`, `kaola-compact-recovery.py` `c45662a4…` (unchanged
  since 055), `kaola-zcode-acp.py` `35815c83…` (unchanged), `kaola-tmux.sh`
  `b03d9fca…`, kimi/devin/codex adapters and platform manifests byte-identical
  to 4b247's. The two integrated fixes verified in the source: the node prompt
  now states "A recovery entry accepts only input, checked, unavailable and
  optional applied; never retained. Put each scope in checked or unavailable,
  never both." plus "Checkpoint only this batch's selected input ids,
  verbatim… With no selected business changes, emit no business entries."
  (commit `9f778981`), and CODEX_HOME preservation through outside launch
  (commit `24a2355a`).
- Consumers: `kimi3/`, `devin3/` — fully-linked fixture (dispatch
  `["qa-prior-reclaim-1"]` only; no seeded gap), seeded only with the src-r3
  state tool; fixture AGENTS.md adds the no-session-control constraint
  (requirement 4) and contains NO checkpoint-shape guidance. Builder:
  `common/build-lane3.sh`. Minimal flow: start → one bounded setup turn
  (installed-Skill reads recorded) → initial business batch settles → native
  `/compact` at a verified idle boundary. No extra verdict/business turns.
- Environment/isolation: every launch scrubbed the inherited worker-binding
  env (`KAOLA_ACP_DISPATCHER`, heartbeat host vars, child record var, provider
  config injections); `KAOLA_ACP_RECORD_ROOT` isolated per bundle. No
  `CODEX_HOME` was explicitly supplied by any launch env, so none was
  preserved or overridden; nodes ran under the same current account through
  the existing standard route. No private-home experiment duplicated, no
  credential bytes printed, no global native config mutated.
- Runtimes (current, unchanged): Kimi CLI 2.1.1 (`kimi acp`, resolved
  `kimi-code/k3` thinking=max, Fast off — none exists), Devin CLI 3000.11.3
  (`devin acp --model swe-2-max`, default tier), codex-cli 0.160.1 as the
  bound maintenance node (`codex/luna`, `--role sideagent`).

## 4. Kimi3 — positive chain (all times UTC 2026-10-06)

Host `kimi-cli-KPR103EK3-orchestrator-main`, holder `5372e6d3…`, ACP
`session_629ddb10…`. Receipts under `kimi3/receipts/` (start/setup/compact/
stop, `chain3-summary.json`); events under `kimi3/records/`.

| Stage | Evidence |
|---|---|
| Initial business batch (seeded revisions 1–3) | node `00976e96…` started @13, batch `b-89e5c253f043` @14 (through=3), checkpoint **verified** @2542 (quiet), node stopped @2547 |
| Setup turn | ended @2541; both installed Skills read and recorded in `qa/progress.md` (kimi skill 10,260 B `90f1c257…`; main 17,407 B `1af732f3…`) |
| Native compaction (explicit route, idle boundary) | prompt `/compact` (fingerprint `52e657bd…`), turn ended @2549; real marker @2551: `Compaction completed.\n- Messages compacted: 10\n- Tokens before: 33,734\n- Tokens after: 24,837` |
| Signal/duty | `compact_reload_detected` @2551 (`kimi-compaction-chunk`, role=host, own session); reload delivered @2549→2552 family; `host_compact_maintenance_registered` @2553 — recovery#1 `kind=host-compaction`, evidence `events.jsonl#2551`, `host_revision` stayed 3 |
| Automatic node | reload turn ended @8769 → fresh node `b1e91af0…` @8771, batch `b-e93d1a2aaa85` @8772 (recovery#1, through=3, recovery-only selection) |
| Checkpoint | **settled VERIFIED** @8773: `settled=[recovery#1]`, `returned_to_host={}`, recovery `unavailable:{}`, checked scopes authorization 6 / duties 7 / links 7 — all real original refs (AGENTS.md, delegator file, state sections, workflow state, ledger, dispatch-index rows, /tmp prior receipts, host events#2551). `host_woken=false` (quiet verified). Node's entries command: clean `{"input":"recovery#1","checked":{…}}` — no `retained` |
| Reclaim | node stopped @8778 (receipt in host events; node record stopped, pid dead); Host exact-stop `kimi3/receipts/host-stop.json`: `stopped:true`, exit 0, `residual_pids:[]` |

## 5. Devin3 — complete chain, honest partial (one bounded attempt)

Host `devin-KPR103ED3-orchestrator-main`, holder `416001bc…`, ACP
`chief-pecorino`. Receipts `devin3/receipts/`, events `devin3/records/`.

- Initial batch `b-eeee66dddfea` (node `1e3f70e0…`): verified @249, stopped
  @254. Setup turn recorded both installed Skills (devin skill 10,438 B
  `061c707d…`; main 17,407 B `1af732f3…`). ACP read exposure stays
  summary-only on this runtime (873 qualification reused; no byte rerun).
- `/compact` at verified idle boundary: turn ended @255 (2 ms), compaction
  `started` @256 → `completed` @257 (`_cognition.ai/compaction`, own session
  `chief-pecorino`, summary path in the raw signal);
  `compact_reload_detected` @258 (role=host), reload @259, duty @261
  (recovery#1, `host_revision` stayed 3).
- Reload turn ended @895 → automatic node `e6c4c42d…` @896, recovery batch
  `b-c54a50ea6976` @897 (recovery#1, through=3).
- Checkpoint: settled **partial** @898 — the entry is VALID (node command
  cursor 960: `{"input":"recovery#1","checked":{…},"unavailable":{"links":
  …}}`, no `retained`; scopes correctly split). Return:
  `recovery#1 → recovery-originals-unavailable` — the node read and cited the
  real /tmp prior receipts but requires a matching local Runner record for
  the seeded `devin-KPR103ED3-prior-diagnostic` session under the consumer's
  own record root, which this fixture does not carry. Alert recorded @901,
  Host woken @900, node stopped @908, Host exact-stop exit 0, residuals [].
- Precise remaining limitation and next recovery: seed the fixture's reclaim
  evidence from one real prior disposable Devin diagnostic run inside the
  SAME record root (real start/stop Runner records), then rerun this same
  one-attempt chain. The mechanism (signal→duty→carrier node→scoped
  checkpoint→reclaim) is fully exercised on this seam; only the fixture's
  local-record evidence sufficiency differs from the verifying kimi3/zcode
  nodes' judgment. No claim is made that Devin "cannot" verify.

## 6. Reuse and boundaries (ZCode/Claude, read-only)

- ZCode: no native rerun. The r1/r2 positive (`b-0adc9f467511` verified on
  `4b247a2d` bridge `35815c83…`, 2026-10-06) stands with its
  controller-binding-setup qualification; `35815c83…` is byte-identical in
  src-r3, so the bridge seam is unchanged. Exposure limit unchanged
  (completed Read events carry no payload).
- Claude: no run (user holds all new Claude starts). The 055 full chain
  remains an old-candidate (`0553a8db`, holder `4ae5543d…`, dispatch
  `71357f28…`, bridge `2135ad71…`, 2026-10-06 dated verification
  `/tmp/kpr-i264-929-host-proof-verification.json`) proof. The 9f/24a changes
  (prompt text, schema-adjacent state tool, CODEX_HOME/launch handling) are
  later affected boundaries with current-runtime coverage from this lane's
  live chains (kimi3 verified; devin3 valid-entry partial) — they are not a
  fresh Claude execution and not a universal unchanged-chain claim. Installed
  Claude Skills remain `1af732f3…`/`68989e48…` (unchanged).
- Background compaction: no claim; only the explicit `/compact` route was
  exercised on every seam.

## 7. Cleanup

- kimi3/devin3 Host stops: exit 0, `residual_pids:[]`; all carrier nodes
  stopped by the carrier with receipts in host events (8778 / 908) and node
  records stopped, pids dead. `pgrep KPR103EK|KPR103EZ|KPR103ED` returns
  none. Prior consumers untouched. The stale devin2 `47d7c688` record is
  left as-is (evidence, not garbage); its pids are confirmed dead.
- No repository, installed, global-config, or consumer-project write outside
  `edge/**`; no install/login/timer/framework; the live KPR Host, its node,
  other lanes, and the core's busy source were never contacted.

## 8. Row contributions (for the one Host table)

- Kimi CLI 2.1.1 + `24a2355a`: outcome 3 **PASS** — automatic chain with
  VERIFIED scoped recovery checkpoint (`b-e93d1a2aaa85`), explicit `/compact`
  trigger, carrier-only node, exact reclaim. Limits: single-run positive;
  background route unmeasured.
- Devin 3000.11.3 + `24a2355a`: outcome 3 chain PASS to scoped checkpoint
  with VALID entry; checkpoint honestly partial (`recovery-originals-
  unavailable`, links — local-record evidence demand). Positive pending the
  fixture-evidence completion in §5; not a support or mechanism claim.
- ZCode 0.16.9: unchanged from r1/r2 (verified checkpoint on 4b247; bridge
  bytes identical in 24a).
