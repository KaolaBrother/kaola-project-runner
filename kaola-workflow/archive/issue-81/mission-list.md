# Goal: Verify and, if real, wire ZCode 3.12+ v4 native steering (guide/sendText) into the Runner ACP steer tool

Run: issue-81 · Issue: #81 · Branch: `workflow/issue-81`
Worktree: `/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-81`
Scope lock: #81 only. Never edit or revert #69 / #74 / #75 / #79 runs, branches, worktrees, or sessions.
Standing constraints: no credential copy/decrypt/print; secrets in memory only, redacted in every
log, receipt, comment, fixture, and evidence file; no global/user ZCode config mutation; no
upstream byte vendoring; no hand-edit of generated `skills/`; no release and no global install;
do NOT finalize/archive/sink before outer ACCEPT.
Concurrency lock: #79 owns `scripts/kaola-zcode-acp.py` until it merges. Phase 1 is read-only
investigation plus isolated experiments only — no edits to the production adapter, generated
Skills, or the #79 worktree; no competing for #79's live test session. Implementation resumes
only after the outer layer confirms a post-#79 main/SHA.

## 1. Receipt contract and current steer surface (read-only)
- item: Consolidate the #65 steer receipt contract (`steer_outcome` / `steer_consumed` / `steer_confirmation` vocabulary: injected, written/write-only, interrupted_and_resent, resent_without_interrupt, started_new_turn, not_consumed, unsupported, rejected, unknown) and inventory the current steer path in `scripts/kaola-tmux.sh`, `scripts/kaola-acp-holder.py`, `scripts/kaola-zcode-acp.py` — where a native v4 steer would slot in without a second lifecycle. Record exact function/field names.
- status: done
- dispatched: self; output lands at `kaola-workflow/issue-81/evidence/01-receipt-contract-and-steer-surface.md` in the main checkout
- result: `evidence/01-receipt-contract-and-steer-surface.md`. Receipt vocabulary and hard rules
  consolidated from `op_steer` + #65 archive; wire shape documented (holder sends
  `{method, params:{sessionId, prompt, _meta.steering.idleBehavior}}`, interprets
  `result.outcome`); minimal-change hypothesis recorded — adapter-side steer entry +
  manifest keys, holder/kaola-acp.py/kaola-tmux.sh untouched.

## 2. Upstream primary-source facts for the v4 steering path
- item: From primary upstream sources only (ZhouXiaolin/zcode-provider `extensions/zcode-provider.ts` + README, william0wang/zcode-acp `docs/PROTOCOL.md` v4 section), extract verbatim: the v4 conversation subscribe request/response, the CAS `setFollowupMode=guide` shape, the `v4/command` `sendText` request/response shape, and the `turn.steerQueued` / `turn.steerDrained` event shapes — plus whatever upstream says about which outcomes mean injected vs queued vs rejected. Record verbatim quotes, file/line, and source URLs/commit pins; no conjecture.
- status: done
- dispatched: explore subagent (read-only web) + direct fetch of the two pinned files; output lands at `kaola-workflow/issue-81/evidence/02-upstream-v4-facts.md` in the main checkout
- result: `evidence/02-upstream-v4-facts.md` (zcode-provider @ c7d06a0, zcode-acp @ 840f9f2).
  Verbatim: guide = `v4/conversation/subscribe`{topic:conversation/<sid>, connectionId,
  clientMode:desktop-continuous} → snapshot frame carries {revision, logEpoch} →
  `v4/command`{type:setFollowupMode, payload:{mode:guide}, baseRevision, baseLogEpoch} (retry on
  status:"stale") → mid-turn `v4/command`{type:sendText, payload:{text}}. All on the same
  app-server stdio NDJSON pipe; `session/steer` removed upstream in 0.16+ ("moved to the v4
  command/conversation API"). Upstream never inspects the sendText result for injected-vs-queued
  — KPR's stricter receipt must read turn.steerQueued/steerDrained itself.

## 3. Installed ZCode 3.12.3 v4 surface (read-only bundle inspection)
- item: In the installed 3.12.3 bundle (`/Applications/ZCode.app/...`), verify the exact v4 method table entries and request schemas the experiment must use: v4 conversation subscribe, `setFollowupMode` (CAS fields), `v4/command` `sendText`, and the `turn.steerQueued`/`turn.steerDrained`/related session-event names. Confirm whether these are reachable over `app-server --stdio` as the Runner spawns it, or gated elsewhere. Read-only; no process start, no credential file opened.
- status: done
- dispatched: self; output lands at `kaola-workflow/issue-81/evidence/03-installed-3123-v4-surface.md` in the main checkout
- result: `evidence/03-installed-3123-v4-surface.md`. v4/* methods ride the SAME app-server
  --stdio dispatchRequest switch as session/* (requireV4Gateway). Command envelope has CAS
  (baseRevision/baseLogEpoch); sendText carries requestedDelivery:startNow|queue|guide;
  steer admission rejects with turn_not_steerable / expected_turn_mismatch; the shared
  zcodeSessionEventTypeSchema enum includes turn.steerQueued{delivery:queue|guide,
  targetTurnId} and turn.steerDrained{targetTurnId, injectedMessageIds}. sendText result
  alone does NOT separate guide-queued from plain-queued — the events do. Open live
  questions recorded for M4.

## 4. Live isolated v4 steering experiment on real ZCode 3.12.3
- item: In a disposable isolated Git repo (not this repo, not any user project, not the #79 test session), drive the real installed ZCode 3.12.3 app-server over the v4 path: create session, start a demonstrably-running turn, send a v4 guide/sendText instruction mid-turn, and record raw sanitized events. The evidence must distinguish, in the same turn: injected (consumed mid-turn), queued (delivered next turn), and rejected/unknown — never a verdict from string-matching alone. Include a negative leg (e.g. idle or non-guide mode) if the surface allows. Exact stop, `residual[]` equivalent, sanitized raw receipts under `kaola-workflow/issue-81/evidence/`.
- status: done
- dispatched: self; probes `evidence/probes/v4-steer-probe{,2}.py`, raw NDJSON + reports at `evidence/live{,2}/`, verdict at `kaola-workflow/issue-81/evidence/04-live-v4-steering-verification.md` in the main checkout
- result: **NATIVE V4 STEERING IS REAL ON 3.12.3 — both entries injected live.** G1 per-command
  `sendText{requestedDelivery:"guide"}` (no session mutation) and G2 upstream CAS
  `setFollowupMode{guide}`+plain sendText both produced `turn.steerQueued{delivery:"guide"}` →
  `turn.steerDrained{injectedMessageIds}` on the SAME `targetTurnId`, and the running turn's own
  `turn.completed` answered the steer codeword. Queued leg: `steerQueued{delivery:"queue"}`, no
  drain, turn kept its own answer — never injected. Rejected leg: `proto.invalidPayload` /
  `proto.sessionNotFound` / `proto.staleRevision`. TRAP MEASURED: sendText ack reports
  `delivery:"queue"` even for admitted guide — the ack alone cannot separate injected from
  queued; the events are the truthful source. Steer events DO arrive on the existing
  `session/event` channel. Two disposable repos, both sessions closed, 0 residual procs,
  no credential in any evidence file.

## 5. Evidence report and minimal implementation proposal
- item: Report to the outer layer: the measured verdict (supported / unsupported / partial), the raw-evidence index, and the minimal implementation plan (where a native v4 steer slots into the existing steer tool, keeping `--steer-mode interrupt` and old-version compat, receipt semantics unchanged). Hold for outer confirmation of safe sync (post-#79 main/SHA) before any production edit.
- status: done
- dispatched: self; output lands at `kaola-workflow/issue-81/evidence/05-report-and-minimal-plan.md` in the main checkout + the report message to the outer layer
- result: Verdict reported: **supported, measurable, both entries live-proven on 3.12.3.** Minimal
  plan recorded: adapter `_session/steering` → `v4/command sendText{requestedDelivery:"guide",
  expectedTurnId}` + steer-event ledger on the existing `session/event` channel; ~6-line holder
  `queued`→`not_consumed` mapping; manifest `native_steering:"supported"` +
  `acp_steer_method:"_session/steering"`; contract tests proving queued/rejected never report
  injected. Deliberately untouched: kaola-acp.py, kaola-tmux.sh, templates, holder lifecycle.
  Receipt `injected` only after `turn.steerDrained{injectedMessageIds}` on the active
  `targetTurnId` — never from the ack's `delivery` field (measured lie). Gated: production edits
  wait for outer-confirmed post-#79 main/SHA.

## 6. (GATED — post-#79 merge + outer confirmed SHA) Minimal adapter implementation
- item: Only if live evidence proves native support and the outer layer confirms the sync point: implement the minimal v4 steer path in `scripts/kaola-zcode-acp.py` on fresh main, wire it into the existing `steer` surface (native mode only where proven), keep interrupt composite and legacy fallback, receipt vocabulary unchanged. Regenerate via `./scripts/render-skills.py --write`.
- status: done
- dispatched: self on the issue-81 worktree after outer sync confirmed `b40813f` (#79 merged); rebased to `513e8e1` when the #80/#82/#83 sinks landed; output lands at `kaola-workflow/issue-81/evidence/06-implementation-validation.md` + `candidate-67ee287.diff` in the main checkout
- result: `evidence/06-implementation-validation.md` §1. `_session/steering` drives the proven
  v4 path on the existing transport: lazy `v4/conversation/subscribe`, `sendText` with
  `requestedDelivery:"guide"` + per-turn `expectedTurnId` CAS (learned from `turn.started`),
  single in-flight ledger correlating `turn.steerQueued`/`steerDrained` by commandId and
  pendingInputId. `injected` requires the same-turn chain (`targetTurnId` match + the steered
  turn + non-empty `injectedMessageIds`); queued→`not_consumed`+`mutation_performed`,
  turn-end/silent→`unknown`, reject→`rejected`+reasonCode, `-32601`→`unsupported`,
  idle→`promptRequired`. No second lifecycle/scheduler/stdin writer; interrupt unchanged;
  manifest declares `native_steering:"supported"`; generated Skills re-rendered.

## 7. (GATED) Focused hermetic tests + full validation + frozen candidate
- item: Extend `tests/contract/` for the proven v4 steer paths (incl. queued/rejected never reported as injected, turn-end race, disconnect → unknown). Run `./scripts/render-skills.py --check` and `./scripts/validate.sh`, record exact outcomes, freeze candidate SHA + sanitized evidence, report for outer review. No finalize/archive/sink.
- status: done
- dispatched: self; failure-first tests on the fake app-server with live-verbatim ack trap + steer legs; output lands at `kaola-workflow/issue-81/evidence/06-implementation-validation.md` + `candidate-6d0002adf7a6c4aad783283eb161ea67dd51587a.diff`
- result: `evidence/06-implementation-validation.md` §2-§4g. Frozen candidate
  `6d0002adf7a6c4aad783283eb161ea67dd51587a` on `18db64b` (origin/main after the
  #85 sink; #85's fail-closed resume ordering preserved). Supersedes `67ee287`,
  `01f6acc`, `8816309`, `e8359e8`, `a7e39c2`, `0a4790e`, `e09f9b9` — NINE
  outer-review findings fixed per outer spec, each failure-first verified red
  on its pre-fix SHA (eight earlier findings plus this round's unvalidated
  env input):
  (a) `record_steer_drained` `None == None` pendingInputId false-positive —
  nonempty pending-id or exact `intent.sourceCommandId` only;
  (b) `same_turn` lenient `expected is None` clause — expected turn identity
  REQUIRED for `injected`;
  (c) mixed-drain attribution — `injected` now requires OUR correlated item's
  own `messageId` inside `injectedMessageIds` (a batch injecting someone
  else's message is not ours);
  (d) queue admission + drain race — `injected` requires the admission to
  report `guide` delivery; `queue`/`admittedDelivery:"queue"` can never be
  this turn's guide injection;
  (e) v4/command ack timeout/transport-uncertain — no longer `-32000`
  `rejected`; falls into the evidence wait: staged admission → `queued`,
  silence → `unknown` + `sendUncertain:true` + do-not-resend reason;
  definitive server rejection still `rejected`, `-32601` still `unsupported`;
  `STEER_TOTAL_BUDGET` caps the exchange under the holder's 30 s;
  (f) turn-change race — target `turn_request_id` captured at entry and
  rechecked immediately before send; the expected-turn wait also breaks on
  target death or a backend-side successor `turn.started`, so no
  `v4/command` is ever sent to a dead or replaced turn (both
  `steer_race_end` and `steer_race_replaced` covered);
  (g) one deadline computed at steer start — every phase (subscribe,
  expected-turn wait, command exchange, drain wait) gets only the remaining
  budget; the command is never sent after the deadline
  (`KAOLA_ZCODE_STEER_BUDGET` exists only for deterministic tests);
  (h) app-server death after a possibly-processed command —
  `BackendTransportError` distinguishes transport loss from explicit
  rejection; death/timeout now resolves `queued`/`unknown`+`sendUncertain`,
  never `rejected`, never resent. Plus the evidence gap: the backend tee
  now persists a strict hash-only whitelist (SHA-256 id fingerprints,
  finite delivery enums, byte counts, text hashes; stderr→DEVNULL;
  unknown/non-JSON→`{kind,bytes}` count-only), proven by a 49-check fixture
  with fake secrets planted in every ID field, ID array, and a
  stderr-shaped line;
  (i) `KAOLA_ZCODE_STEER_BUDGET` was an unvalidated production input —
  `float(env)` at import crashed on `invalid` (outer reproduced exit 1)
  and any value >30 s defeated the holder-safe deadline; now
  `_steer_budget_seconds` resolves invalid/non-finite/non-positive input
  to the 26 s default and clamps every value to ≤26 s, so no env content
  can crash startup or outlive the holder's 30 s (no new config layer;
  the compressed `=5` test path unchanged).
  Adversarial legs `steer_phantom`, `steer_noexpect`, `steer_mixed`,
  `steer_qdrain`, `steer_timeout_staged`, `steer_timeout_silent`,
  `steer_race_end`, `steer_race_replaced`, `steer_exit_staged`,
  `steer_exit_silent`, `steer_slow_subscribe`, `steer_slow_exchange` each
  re-verified red on the pre-fix adapter (raw reds:
  `evidence/review3/red-a7e39c2.txt`, `evidence/review4/red-0a4790e.txt`,
  `evidence/review6/red-e09f9b9.txt`); `steer_guide_nopid`/`steer_guide`
  prove no over-block. On `6d0002a`: 71 zcode contract tests OK (36
  steer/knob tests incl. the static 27-value hostile-input table);
  `test-issue-84` 18 OK, `test-issue-85` 7 OK, `test-issue-74` 151
  assertions 0 failed — #84/#85/#74 preserved; `render-skills.py --check`
  PASS; `validate.sh` PASS unmitigated exit 0, zero residual. Fresh
  byte-bound live proof on the new bytes (`evidence/live6-adapter/`): the
  integrated adapter against real ZCode.app 3.12.3 through the hardened
  tee returned `injected`/`agent-confirmed`; `backend-tee.jsonl` +
  `backend-evidence.json` show the real `sendText`→`steerQueued`→
  `steerDrained` chain correlated entirely by SHA-256 fingerprints
  (commandId, turn, pending-input, text all match; all five cross-checks
  pass) with zero raw ids/text/stderr persisted, and the model answered the
  steer codeword mid-turn. No finalize/archive/sink; awaiting outer
  ACCEPT.
