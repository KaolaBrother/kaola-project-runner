# Finalization summary — bundle-69 (Issue #69)

## Delivered

Honest live evidence for the three remaining ZCode Host event-wake legs of Issue #69,
executed against real ZCode 3.12.3 / CLI 0.16.5 through the post-#79 adapter at candidate
`b40813f` (measured bytes identical at merge base `88042cd`; adapter/holder scripts
unchanged `b40813f..main`):

- **Leg A — real ACP `turn_failed`: PROVEN.** Worker app-server killed under a live
  adapter → real ACP JSON-RPC error `{-32603 "internal error: [Errno 32] Broken pipe"}` →
  holder `turn_failed` → host event `idle/14 outcome=turn_failed` staged(28) →
  delivered(29) → confirmed(36). Baseline `idle/13` and `terminated/15` chains complete.
- **Leg B — unconfirmed event redelivery after holder resume: PROVEN.** `idle/19`
  staged(107) → holder force-stopped while unconfirmed(108) → `start --resume zcode-1` →
  `worker_event_restored`(109) → `worker_event_delivered`(110) →
  `worker_event_confirmed`(129).
- **Leg C — duplicate dedup, single consumption/ack: PROVEN.** Real worker event
  `idle/14` staged(17) on a busy host → byte-identical carrier replay on the host socket →
  raw reply `{"duplicate":true,"pending":1}` → exactly one lifecycle delivered(150) →
  confirmed(169). Boundary also measured: identical replay after ack re-stages
  (`staged:true`, 170→171→177) — dedup authority spans the pending window only
  (at-least-once semantics).

All six holder/worker exact-stop receipts report `residual_pids: []`. Prior pre-#79
BLOCKED results are preserved unchanged in the mission list; the post-#79 results are
recorded as separate rows.

## Files Changed

No production files changed. Run artifacts only:

- `kaola-workflow/bundle-69/mission-list.md` — appended post-#79 rows (prior rows immutable)
- `kaola-workflow/bundle-69/evidence/` — raw sanitized receipts, holder event logs,
  reports (68 files, ~416K): `20-post79-live-legs-report.md`, `00-diagnosis-report.md`,
  `pre79/` (blocked-run receipts + holder records), `legA|legB|legC/` (receipts + records),
  `legC/replay-worker-event.py`
- `kaola-workflow/bundle-69/.cache/` — `final-validation.md`, `doc-docking.md`
- `kaola-workflow/bundle-69/finalization-summary.md` — this file

## Test Coverage

Issue acceptance legs are the three live legs above — machine receipts in
`evidence/leg{}/` and the host `events.jsonl` cursor chains are the covering proof; the
offline contract tests (`test_resume_redelivers_unconfirmed_events`,
`test_bounded_queue_dedup_and_single_batch_flush`) remain supplementary, never claimed as
live. Nothing in the issue statement is left unexecuted: all three legs ran against the
real stack.

## Validation

- `verdict: pass` — `./scripts/render-skills.py --check && ./scripts/validate.sh`
  (recorded in `.cache/final-validation.md`,
  `validated_candidate_hash: ab507eb3…`, measured on worktree `88042cd`)
- Live leg receipts: see Delivered — A (cursors 28/29/36), B (107→109→110→129),
  C (17→150→169 + `duplicate:true` raw reply); outer reviewer independently re-verified
  the same cursors and 7 exact-stop `residual_pids: []` before ACCEPT.
- Unexecuted: none required. Live tmux smoke was covered by the leg sessions themselves
  plus a pre-flight smoke session.

## Changed Paths

(Filled by the finalize transaction.)

## Documentation Docking

`.cache/doc-docking.md` → **DOCKED** — no public behavior changed; README/docs/CHANGELOG/
generated skills unaffected.

## Follow-Up Items

- **filed: #84** — `fix: ZCode 3.12+ 原生会话 resume 恢复模型配置` (already opened; not
  modified by this run). Observed defect: faithful native-session resume on real
  ZCode 3.12.3 — `session/read` returns a message-list shape without `settings`, so
  `hydrate_settings()` recovers no persisted model and `reregister_provider` fails closed;
  `runtimeModel` `setModel` → ZodError (dead protocol); account-path `setModel` →
  `Provider Registry 中不存在 Model` (provider never re-registered on resume). Raw-wire
  probe evidence in `evidence/legB/receipts/09|10-probe-resume-read*.txt`. Does not
  affect leg B's verdict (holder-level event restoration proven on the `start --resume`
  path).

## Readiness

All Issue #69 legs live-proven; validation PASS; docs docked; follow-up filed.
Ready for archive + merge sink; Issue #69 closes on sink (acceptance received from outer
reviewer).

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/bundle-69/.cache/doc-docking.md
- kaola-workflow/archive/bundle-69/.cache/final-validation.md
- kaola-workflow/archive/bundle-69/.cache/mirror-digest.json
- kaola-workflow/archive/bundle-69/.cache/origin/selection-record.json
- kaola-workflow/archive/bundle-69/evidence/00-diagnosis-report.md
- kaola-workflow/archive/bundle-69/evidence/20-post79-live-legs-report.md
- kaola-workflow/archive/bundle-69/evidence/legA/receipts/01-host-start.json
- kaola-workflow/archive/bundle-69/evidence/legA/receipts/02-host-bootstrap.json
- kaola-workflow/archive/bundle-69/evidence/legA/receipts/03-worker-start.json
- kaola-workflow/archive/bundle-69/evidence/legA/receipts/04-worker-baseline.json
- kaola-workflow/archive/bundle-69/evidence/legA/receipts/05-appserver-after-kill.txt
- kaola-workflow/archive/bundle-69/evidence/legA/receipts/05-appserver-before-kill.txt
- kaola-workflow/archive/bundle-69/evidence/legA/receipts/06-worker-send-turnfailed.json
- kaola-workflow/archive/bundle-69/evidence/legA/receipts/07-worker-stop.json
- kaola-workflow/archive/bundle-69/evidence/legA/receipts/08-host-stop.json
- kaola-workflow/archive/bundle-69/evidence/legA/records/zcode/zcode-kaola-i69a-host/accefc5ae288d375/events.jsonl
- kaola-workflow/archive/bundle-69/evidence/legA/records/zcode/zcode-kaola-i69a-host/accefc5ae288d375/record.json
- kaola-workflow/archive/bundle-69/evidence/legA/records/zcode/zcode-kaola-i69a-worker/accefc5ae288d375/events.jsonl
- kaola-workflow/archive/bundle-69/evidence/legA/records/zcode/zcode-kaola-i69a-worker/accefc5ae288d375/record.json
- kaola-workflow/archive/bundle-69/evidence/legB/receipts/01-host-start.json
- kaola-workflow/archive/bundle-69/evidence/legB/receipts/02-host-bootstrap.json
- kaola-workflow/archive/bundle-69/evidence/legB/receipts/03-worker-start.json
- kaola-workflow/archive/bundle-69/evidence/legB/receipts/04-host-busy-send.json
- kaola-workflow/archive/bundle-69/evidence/legB/receipts/05-host-status-busy.json
- kaola-workflow/archive/bundle-69/evidence/legB/receipts/06-worker-send-evt1.json
- kaola-workflow/archive/bundle-69/evidence/legB/receipts/07-host-force-stop.json
- kaola-workflow/archive/bundle-69/evidence/legB/receipts/08-host-resume-attempt.json
- kaola-workflow/archive/bundle-69/evidence/legB/receipts/09-probe-resume-read.txt
- kaola-workflow/archive/bundle-69/evidence/legB/receipts/10-probe-resume-read2.txt
- kaola-workflow/archive/bundle-69/evidence/legB/receipts/11-errored-holder-stop.json
- kaola-workflow/archive/bundle-69/evidence/legB/receipts/12-host-restart.json
- kaola-workflow/archive/bundle-69/evidence/legB/receipts/13-host-bootstrap2.json
- kaola-workflow/archive/bundle-69/evidence/legB/receipts/14-host-busy-send.json
- kaola-workflow/archive/bundle-69/evidence/legB/receipts/15-worker-send-evt2.json
- kaola-workflow/archive/bundle-69/evidence/legB/receipts/16-host-force-stop2.json
- kaola-workflow/archive/bundle-69/evidence/legB/receipts/17-host-resume-zcode1.json
- kaola-workflow/archive/bundle-69/evidence/legB/receipts/18-worker-stop.json
- kaola-workflow/archive/bundle-69/evidence/legB/receipts/19-host-stop.json
- kaola-workflow/archive/bundle-69/evidence/legB/records/zcode/zcode-kaola-i69b-host/61a887d8f07c832a/events.jsonl
- kaola-workflow/archive/bundle-69/evidence/legB/records/zcode/zcode-kaola-i69b-host/61a887d8f07c832a/record.json
- kaola-workflow/archive/bundle-69/evidence/legB/records/zcode/zcode-kaola-i69b-worker/61a887d8f07c832a/events.jsonl
- kaola-workflow/archive/bundle-69/evidence/legB/records/zcode/zcode-kaola-i69b-worker/61a887d8f07c832a/record.json
- kaola-workflow/archive/bundle-69/evidence/legC/receipts/01-host-start.json
- kaola-workflow/archive/bundle-69/evidence/legC/receipts/02-host-bootstrap.json
- kaola-workflow/archive/bundle-69/evidence/legC/receipts/03-worker-start.json
- kaola-workflow/archive/bundle-69/evidence/legC/receipts/04-host-busy-send.json
- kaola-workflow/archive/bundle-69/evidence/legC/receipts/05-worker-send-evt1.json
- kaola-workflow/archive/bundle-69/evidence/legC/receipts/06-replay-duplicate.txt
- kaola-workflow/archive/bundle-69/evidence/legC/receipts/07-host-wait.json
- kaola-workflow/archive/bundle-69/evidence/legC/receipts/08-replay-post-confirm.txt
- kaola-workflow/archive/bundle-69/evidence/legC/receipts/09-worker-stop.json
- kaola-workflow/archive/bundle-69/evidence/legC/receipts/10-host-stop.json
- kaola-workflow/archive/bundle-69/evidence/legC/records/zcode/zcode-kaola-i69c-host/adfef59454c34f07/events.jsonl
- kaola-workflow/archive/bundle-69/evidence/legC/records/zcode/zcode-kaola-i69c-host/adfef59454c34f07/record.json
- kaola-workflow/archive/bundle-69/evidence/legC/records/zcode/zcode-kaola-i69c-worker/adfef59454c34f07/events.jsonl
- kaola-workflow/archive/bundle-69/evidence/legC/records/zcode/zcode-kaola-i69c-worker/adfef59454c34f07/record.json
- kaola-workflow/archive/bundle-69/evidence/legC/replay-worker-event.py
- kaola-workflow/archive/bundle-69/evidence/pre79/01-host-start.json
- kaola-workflow/archive/bundle-69/evidence/pre79/02-host-stop-wall1.json
- kaola-workflow/archive/bundle-69/evidence/pre79/03-host-start-shim.json
- kaola-workflow/archive/bundle-69/evidence/pre79/04-host-stop-shim.json
- kaola-workflow/archive/bundle-69/evidence/pre79/10-probe-spawn-crash.txt
- kaola-workflow/archive/bundle-69/evidence/pre79/11-probe-model-and-turn.txt
- kaola-workflow/archive/bundle-69/evidence/pre79/holder-records/5dc4ca1c20261ece/events.jsonl
- kaola-workflow/archive/bundle-69/evidence/pre79/holder-records/5dc4ca1c20261ece/record.json
- kaola-workflow/archive/bundle-69/finalization-summary.md
- kaola-workflow/archive/bundle-69/mission-list.md
- kaola-workflow/archive/bundle-69/workflow-state.md
