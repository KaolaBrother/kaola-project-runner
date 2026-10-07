# Issue #263 — consolidated original delivery, 2026-10-05

Implemented feasible noninterrupting input for all ten supported runtimes. Host acceptance,
outer personal review, Opus review, and normal closeout remain pending. This is a bounded worker
result. It does not accept the project.

## Candidate and custody

Candidate: ca7489ef8336e099698f37ea0d706717688be712 on workflow/issue-263.
Base: normal main dad228e4 at the original claim.
Original candidate 1f3f1fb0eec031ed863b07d805e70413658eeae2 and its delivery remain unchanged.
Expansion commits: ffb67a4a, 52092c4f, f817b58f, then this candidate.

- Own worktree: /Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-263.
- Original claim: /Users/ylmacstudio/Workspace/kaola-project-runner/kaola-workflow/issue-263/workflow-state.md.
- Same ledger: /Users/ylmacstudio/Workspace/kaola-project-runner/kaola-workflow/.ledger/issue-263.jsonl.
  Mission 1 DONE is immutable. Mission 2 records the owner-expanded adaptation outcome.
- Full patch: /tmp/kpr-i263-all-runtime-candidate.patch.
- Diff summary: /tmp/kpr-i263-all-runtime-diffstat.txt.
- Final hashes: /tmp/kpr-i263-all-runtime-source-sha256.json.
- Original two-runtime delivery: /tmp/kpr-steer-adaptation-delivery-20261005.md.

I resumed installed Workflow Next and the same claim. I made no new claim or intake.
Product writes stayed in my worktree. The main checkout's only writes were this run's ledger.
No merge, finalize, archive, issue closure, release, or install occurred.

## Result and evidence scope

The owner permits processing in the current step, a later step, or a later turn when delivery
does not cancel, stop, or restart the agent and preserves the exact session and ongoing work.
The old same-turn-only classification is removed. Admission, processing, and original request
ownership are separate facts. Stronger original-turn Grok/OpenCode proofs remain valid.

| Runtime | Product route | Processing evidence and limit |
| --- | --- | --- |
| Codex | Existing native _session/steering | Accepted working route, reused. /tmp/kpr-codex-host-steer-20261005.json reports same active request 7 and agent-confirmed consumption. No new native test. |
| Claude Code | Existing streamed input through its ACP bridge | Accepted working adoption proof, reused. Write-only acknowledgment remains narrower than processing. No native rewrite or retest for version drift. |
| ZCode | Existing KPR ACP _session/steering | Accepted working guide/drain route, reused. Queue admission alone has null consumption. No bridge rewrite or native retest. |
| Grok 1.0.46 | _x.ai/interject with top-level sessionId and text | Original KPR request 5 ended with ADOPTED-263. Native queued reply alone is admission. Native capability proof reused. |
| OpenCode 2.0.22 | KPR-owned ACP extension and local V2 session.prompt with delivery steer and resume false | Original KPR request 4 ended with ADOPTED-263. Native admitted reply alone is admission. Adapter/plugin bytes unchanged. |
| Devin 3000.11.3 | Second supported standard session/prompt on the exact session | New KPR mapping proved original tool completion and ADOPTED-263. Requested swe-2-max; advertised swe-2-high. Preserve measured scope. |
| Droid 0.233.0 | Second supported standard session/prompt on the exact session | New KPR mapping proved token processing, original tool exit 0, and both replies. Exact native turn number is not required. Raw tool status contradicts model prose; retain both below. |
| Cursor 2026.09.28-64d2043 | Local pending input, then standard prompt after original completion | Actual original tool/request completed. New owned prompt processed ADOPTED-263 on the same session. No native active ACP input route was found. No concurrent-cancel probe repeated. |
| Kimi CLI 2.1.1 | Local pending input, then standard prompt after original completion | Actual original tool/request completed. New owned prompt processed ADOPTED-263 on the same session. New admission-guard KPR proof passed. Separate web REST routes do not bind this ACP session. |
| DSH 0.2.0-rc.2 | KPR-owned ACP extension and in-process agent.steer plugin | Final integrated KPR request 4 preserved its tool, processed ADOPTED-263, and ended normally. Native route proof reused, not repeated. |

Accepted prior scope is in /tmp/kpr-acp-research-synthesis-20261005.md and later owner corrections.
Its older refusal-only Droid/Devin/DSH classifications are superseded by original raw concurrent
prompt and DSH bridge results. Its old compact-hook limit does not override current native
automatic recovery evidence.

## Source and adaptation

I read the original unresolved reports and raw frames before changes:
- /tmp/kpr-unresolved-dsh-devin-steer-20261005.md.
- /tmp/kpr-unresolved-droid-kimi-steer-20261005.md.
- /tmp/kpr-unresolved-steer-host-review-20261005.md.

The original Grok native success and research remain at
/tmp/kpr-grok-underscore-probe-receipt.json and /tmp/kpr-acp-research-20261005.md.
Pinned Paseo remains f24bb523e86f379f3e5a12a40ecd505a0797d269.
Its providers/opencode/v2/turns.ts:323 calls supported session.prompt with delivery steer.
The original two-runtime report retains source extracts, exact plugin exposure, and hashes.

Devin's /tmp/kpr-steer-devin-out/frames.jsonl shows standard concurrent input, model processing,
and coalesced replies. Droid's /tmp/kpr-diag-droid-20261005/probe.raw.jsonl shows ZULU9,
original tool exit 0, and both prompt ends without transport cancellation before processing.
Their KPR mapping sends only sessionId plus standard prompt text blocks, with no invented
vendor method or steering metadata. A bounded wait can return written/write-only and null
consumption. A late steer_reply remains in the existing event log under its own request id.
It never settles or replaces the primary prompt owner. Completion alone does not prove model
processing. Execution errors retain unknown effects and are not replayed.

I read the Cursor/Kimi handoff, final patch, and Host judgment:
- /tmp/kpr-i263-cursor-kimi-route-delivery.md.
- /tmp/kpr-i263-cursor-kimi-patches/0001-issue-263-steer-queue-mode.patch,
  SHA-256 337d8d21c5ba08f8cbb626c46b3d19eee601b6945b09937e8fe21df6dea13c3e.
- /tmp/kpr-i263-cursor-kimi-host-review-20261005.md.

Its 4 queue fixtures, 27 steering tests, and render/generated PASS remain scratch collaboration
evidence. I did not copy its new queue mode. The smaller existing steer operation carries the
manifest's after-turn delivery for Cursor/Kimi. Installed Cursor ACP cancels on a second prompt;
Kimi rejects it with turn.agent_busy. The product writes no concurrent native prompt.

One local operation waits on the existing prompt completion condition. It calls ordinary prompt
admission once. Inside that actual admission lock, it checks the expected prior request, exact
ACP session, and holder. A different request that starts AND ends before admission gets no write.
No recursive holder lock or global serialization is added. A failed or cancelled original gets
no follow-up write. Its actual outcome and stop reason are in steer_followup.original_turn.
A successful follow-up has its own new request id and terminal state.

Local queued means local pending admission only, with steer_native_written false. It makes no
future request-preservation claim. It is not native queue admission. The original Kimi web 2.1.1
OpenAPI route evidence is in a separate process. It does not bind the owned ACP session. No HTTP
or PTY transport replacement occurred. Exact source snippets and non-model route receipts remain
in /tmp/kpr-i263-cursor-kimi-patches/.

The DSH original handoff is /tmp/kpr-i263-dsh-route-delivery.md,
SHA-256 a06728979575b140a1682639d0028dfad955d6d7959a713c34ce884ff592b66a.
I read its out/frames.jsonl, out/bridge.jsonl, out/session-events.jsonl, and installed
dsh-agent-loop, dsh-acp, dsh-api-session-controller, dsh-app-boot, and dsh-llm source.
The supported native call is agent.steer(message), the same call as the shipped controller.
The documented --patch overlay loads the plugin in the SAME native ACP process.

Product files kaola-dsh-acp.py and kaola-dsh-steer.mjs expose a KPR-owned _session/steering
extension. It is not a vendor ACP method. The adapter reuses the unchanged ACP forwarder's
exact request/session guard. Project communication stays ACP stdio through one holder.
The private internal plugin socket is not another independently controlled worker transport.
The exact DSH_BIN gets --profile acp and a private --patch overlay. No profile/global config
changes. Native ACP keeps the original stream, permission traffic, and prompt reply ownership.

Socket success becomes written/native-admitted with null consumption. It never means consumed
true. I changed the scratch acknowledgment label to native-steer: installed native send can
route to next-turn after an independent abort, so a returned call alone cannot promise an exact
next-step target. The original durable log still proves ordinary next-step admission and
processing. A native idle race opens a detached turn and reports started_new_turn; it cannot
prove original-request consumption. Local idle/foreign/replaced guards write nothing.
Possible-write socket errors, internal errors, and uncorrelated replies are unknown and are
not replayed. Native EOF removes the private plugin, overlay, and socket directory.

## Original outputs and evidence

The next section contains original returned language. Concatenation reflects ACP chunks.

Grok:
```text
I'll run a 15-second sleep and wait until it finishes before replying.ADOPTED-263
```
Original start/write/reply/end/stop receipts: /tmp/kpr-i263-grok-final-receipts.jsonl.
Original events: /tmp/kpr-i263-live-records/grok/grok-KPR-i263-final-proof/0ae6cd46e2e144b6/events.jsonl. Original holder record: /tmp/kpr-i263-live-records/grok/grok-KPR-i263-final-proof/0ae6cd46e2e144b6/record.json.

OpenCode:
```text
ADOPTED-263
```
Original start/write/reply/end/stop receipts: /tmp/kpr-i263-opencode-final2-receipts.jsonl.
Original events: /tmp/kpr-i263-live-records/opencode/opencode-KPR-i263-final2-proof/8698cf830258e765/events.jsonl. Original holder record: /tmp/kpr-i263-live-records/opencode/opencode-KPR-i263-final2-proof/8698cf830258e765/record.json.

Devin:
```text
Running the single command as requested.ORIGINAL-263
ADOPTED-263
```
Original start/write/reply/end/stop receipts: /tmp/kpr-i263-devin-affected3-receipts.jsonl.
Original events: /tmp/kpr-i263-expanded-live-records/devin/devin-KPR-i263-affected3/a09d61e1d3bf16e8/events.jsonl. Original holder record: /tmp/kpr-i263-expanded-live-records/devin/devin-KPR-i263-affected3/a09d61e1d3bf16e8/record.json.

Droid:
```text
The tool reported the command was cancelled, so I can’t confirm it finished.

ADOPTED-263
ORIGINAL-263ADOPTED-263
```
Original start/write/reply/end/stop receipts: /tmp/kpr-i263-droid-affected3-receipts.jsonl.
Original events: /tmp/kpr-i263-expanded-live-records/droid/droid-KPR-i263-affected3/00d0f5196b3165f6/events.jsonl. Original holder record: /tmp/kpr-i263-expanded-live-records/droid/droid-KPR-i263-affected3/00d0f5196b3165f6/record.json.

Cursor:
```text
我只运行这一条命令，并等它结束后回复。ORIGINAL-263ADOPTED-263
```
Original start/write/reply/end/stop receipts: /tmp/kpr-i263-cursor-cli-after-turn-receipts.jsonl.
Original events: /tmp/kpr-i263-expanded-live-records/cursor-cli/cursor-cli-KPR-i263-after-turn/6c98831102e21c8d/events.jsonl. Original holder record: /tmp/kpr-i263-expanded-live-records/cursor-cli/cursor-cli-KPR-i263-after-turn/6c98831102e21c8d/record.json.

Kimi admission guard:
```text
ORIGINAL-263The original command already completed on its own (`ORIGINAL-TOOL-DONE`, ~15s wall time). Nothing was cancelled, and I'm not running anything further.

ADOPTED-263
```
Original start/write/reply/end/stop receipts: /tmp/kpr-i263-kimi-cli-admission-guard-receipts.jsonl.
Original events: /tmp/kpr-i263-expanded-live-records/kimi-cli/kimi-cli-KPR-i263-admission-guard/4deed52cd3ac6978/events.jsonl. Original holder record: /tmp/kpr-i263-expanded-live-records/kimi-cli/kimi-cli-KPR-i263-admission-guard/4deed52cd3ac6978/record.json.

DSH native adapter:
```text
ORIGINAL-263 ADOPTED-263

The original command (`sleep 15; echo ORIGINAL-TOOL-DONE`) already completed and returned `ORIGINAL-TOOL-DONE`; nothing was cancelled or stopped, and no further tools were run.
```
Original start/write/reply/end/stop receipts: /tmp/kpr-i263-dsh-native-adapter-receipts.jsonl.
Original events: /tmp/kpr-i263-expanded-live-records/dsh/dsh-KPR-i263-native-adapter/8c92b2310e943ceb/events.jsonl. Original holder record: /tmp/kpr-i263-expanded-live-records/dsh/dsh-KPR-i263-native-adapter/8c92b2310e943ceb/record.json.

The Droid model said its tool was cancelled. Original tool_call_update cursor 23 instead reports
completed, ORIGINAL-TOOL-DONE, and [Process exited with code 0]. Original request 5 ended with
end_turn. I preserve both facts. The raw tool receipt proves preserved work in this case.
Model prose does not prove cancellation. No transport cancel preceded processing.

Original identity and result aggregates:
- /tmp/kpr-i263-final-proof.json — unchanged Grok/OpenCode proof.
- /tmp/kpr-i263-expanded-standard-proof.json — Devin/Droid KPR proof and late replies.
- /tmp/kpr-i263-expanded-after-turn-proof.json — first actual Cursor/Kimi/DSH later-turn proofs.
- /tmp/kpr-i263-final-affected-proof.json — admission guard and final DSH adapter proof.
- /tmp/kpr-i263-final-live-source-comparison.json — recorded/current full source hashes.

Final DSH proof holder, CLI, adapter, and plugin hashes match this candidate exactly.
Kimi's new admission-guard proof ran before removal of provisional #264 code and the DSH-only
mapping. Its holder/CLI full hashes differ. It proves the unchanged guarded queue path.
Final regressions verify that path in this candidate. It is not a full-byte final-holder live
proof. Older later-turn receipts retain their original queue metadata. Final tests prove the
corrected no-preservation claim and actual original outcome boundary. Grok/OpenCode adapter and
manifest hashes stay unchanged. Their mapping/guards remain covered by the final focused check.
No native success was rerun solely for version drift or to restate acceptance.

## Meaningful checks

| Check | Final result | Receipt |
| --- | --- | --- |
| Render write | PASS | /tmp/kpr-i263-final-render-write.txt |
| Render check and byte budgets | PASS | /tmp/kpr-i263-final-render-check.txt |
| Generated Skill acceptance | PASS | /tmp/kpr-i263-final-generated-check.txt |
| Mapping, late replies, no replay, admission races, failure truth, DSH adapter | 28 PASS | /tmp/kpr-i263-final-mapping-check.txt |
| DSH permission/model/resume/binary launch and overlay | 41 PASS | /tmp/kpr-i263-final-dsh-check.txt |
| Capability/permission references | 38 PASS | /tmp/kpr-i263-final-permission-check.txt |
| Queue/turn-end/unrelated-drain admission receipts | 3 PASS | /tmp/kpr-i263-final-queue-check.txt |
| Existing request attribution races | 7 PASS | /tmp/kpr-i263-final-race-check.txt |
| Runner manifest/render checks | 4 PASS | /tmp/kpr-i263-final-runner-check.txt |
| Python compile, Node plugin syntax, git diff check | PASS | Direct command exits 0 |
| Final DSH KPR processing and exact cleanup | PASS | /tmp/kpr-i263-final-affected-proof.json |

The new admission regression arranges a competing turn that starts AND ends before admission.
It proves no write, no cancel, and no replay. Other rows cover a busy competing request, stopped
holder, failed/cancelled prior work, exact session guards, unknown effects, late replies, exact
binary/overlay, native EOF, and private cleanup. All generated files came from render.

The prior full validate.sh result remains EXIT 1 at /tmp/kpr-i263-validate.txt. Its two failed
suites were repaired and checked in the original delivery. It was not rerun for this expansion.
During provisional #264 composition, the offline ZCode suite ran 77 rows and found one old
same-turn-only assertion for an unrelated drain. That row now keeps admission separate from
consumption. It passes with the other 2 affected receipt rows. The original 77-row receipt
/tmp/kpr-i263-compose-test-zcode-acp-contract.py.txt remains a failed run, not a claimed PASS.

Old DSH direct-launch/unsupported assertions and one permission launch assertion also failed
when the local adapter was added. The final affected suites pass after their assertions were
updated to check exact native binary, local overlay, and admission. No final whole-suite PASS
is claimed. Bash 3.2 prerequisite limits remain named in the original full receipt. No missing
prerequisite was installed. Interim #264 composition checks stay scoped to that removed code.

## Cleanup and recovery limits

Diagnostics ran sequentially, with fresh process and endpoint evidence before start. They used
only owned temporary roots, exact sessions, endpoints, and process groups. Original start,
write, reply, original end, and stop are retained. Admission alone never proved processing.
No unknown mutation was replayed.

/tmp/kpr-i263-final-cleanup.json combines 9 owned expansion diagnostics. It includes 2 early
Devin driver errors that wrote no steer. Their original work completed and exact stop was
reconciled before new disposable attempts. The aggregate retains exact stops and empty PID
checks. Cursor stop returned agent_exit_code 143 with residual_pids []. Other expansion stops
returned exit 0 with residual_pids []. Original Grok/OpenCode stops also returned exit 0 and
residual_pids []. DSH helper native children 81997/32913 were reclaimed by their owner; original
cleanup is in its handed-off report. I controlled no other worker seat. No persistent runtime
fault, authentication retry, or quota recovery is claimed.

A stopped holder loses local pending input. A competing, failed, or cancelled prior request gets
no follow-up write. Read existing queue/follow-up events before recovery. A known no-write receipt
permits an Agent-chosen new send. Unknown effects require reconciliation. There is no timer,
count ledger, retry scheduler, automatic interrupt fallback, or new history store.

A running holder keeps its loaded code. A live holder without steer-after-turn/1 refuses this
new delivery operation before a concurrent prompt could be written. This check applies only to
that missing operation. It is not a version gate for accepted native routes. Adopt a new holder
at a safe boundary. No consumer was restarted. Direct custom native ACP commands omit local
adapters. OpenCode V1, other V2 builds, and other DSH builds remain unverified.

Local guards create no atomic native-turn promise. A turn-end race with later processing can
still be valid. Read original request state and session output. A detached native turn has an
explicit ownership limit. Exact native-turn atomicity is not invented as an acceptance condition.

## Independent #264 and integration boundaries

I read provisional #264 candidate cbea806041948a92e1679051120783fd33a2e566, its original report,
helper/bridge source, shared patches, and composition fixture. I composed the handoff and ran
offline checks. Later Host judgment /tmp/kpr-return674-3961-host-review-20261005.md rejects blind
adoption and confirms that the current Codex ACP Host marker already causes a full current
installed Skill reread and task continuation.

All provisional #264 product changes are removed from this candidate. No duplicate compaction
capability, injection, helper, ZCode bridge change, or #264 test registration remains.
Original handoff and interim receipts remain at their original paths. Offline delivery does not
prove model reread/use. Corrected shared #264 handoff is pending with its original owner.
This #263 delivery does not complete or accept #264 and imposes no source barrier.

Frozen 83d64f73 and its full r4 are untouched. No unaccepted #259 hunk was bulk merged.
I did not change #259 claim or its 3 DONE ledger lines. Its ledger SHA-256 remains
320d1c99a0687a72350c14ea836a0c7b08075779bbd08a1235eebdf1ddb3a35f.
The common-holder build tuple and ordinary admission need normal Host composition with
independently owned #259 and corrected #264 changes. The original overlap assessment is in the
two-runtime delivery. Host owns integrated acceptance and the restart note.

Protected untracked main files remain in place. This candidate changes no kaola-dispatch.py,
kaola-record-contract.py, kaola-zcode-acp.py, frozen golden, routine JSON, or CHANGELOG/#258
Unreleased content. No login, global config, other seat control, timer, release, publication,
installation, grant change, or consumer intervention occurred.

Workflow project: issue-263.
Issue: 263.
Branch: workflow/issue-263.
Mission ledger at delivery: 2 done / 0 in-flight / 0 todo / 0 blocked / 0 failed.
Next: Host judges original evidence and composes independent accepted changes. Outer personal
plus Opus review and lifecycle acceptance precede finalize or the conditionally authorized release.
