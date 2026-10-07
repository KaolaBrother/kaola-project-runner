# #271 real QA chain — complete evidence (2026-10-07)

The bounded gap named in the PARTIAL ruling, closed with real receipts:

1. **execute (real admission)**: item `i271-chain` on the Droid shared Elite grant (default/opus/core, count 1 — NOT the worker pool), holder `5e0b9cf369554e6ab702be68cbda0db8`, prompt fp `sha256:388312cc…`, repo = this KPR repo, dispatcher = this Host. Exec receipt `/tmp/chain-exec.json`.
2. **Attributable non-empty result**: `/tmp/kpr-271-chain-result.md` (541 B, 3 original sentences — including a genuine undocumented-step finding below).
3. **collect by ORIGINAL correlation — CORRECTED** (two receipts, honestly reported): the execute receipt's original `dispatch_event_cursor` is **8**. My first index mistakenly used 224 (the seat's post-completion cursor) — that run (`chain-collect5`, since=224) returned turn_completed/end_turn/no-unknowns but was NOT the original-cursor range and is withdrawn as evidence of full-range reading. The corrected run with cursor 8 (`chain-collect7`, since=8, exit 0): outcome `stopped`, stop_reason `end_turn`, `unknown_reasons: ["event-range-unavailable"]` — the seat has since been exact-stopped and its event rotation no longer retains the cursor-8 range, so the tool honestly reports the range unavailable rather than fabricating coverage; retained counts are 0 failures / 0 permissions over the retained range. The 541 B attributable result, same-holder/same-prompt binding, and the end_turn/stop evidence all stand from the originals.
4. **Tool exact-stop + residual**: guarded stop with the full holder id → `stopped: true, exit 0, residual_pids []`.

## Genuine undocumented-step finding (from the chain worker + the collect authoring)

CORRECTION on the earlier "undocumented three fields" claim: the execute receipt ALREADY carries `dispatch_event_cursor`, `prompt_fingerprint`, and `repo` on the item — the binding fields are available from the tool's own original output. My three corrections were artifacts of building the index by hand instead of using the execute receipt's fields verbatim; the real gap was my authoring, not missing documentation. The remaining doc candidate (minor): dispatch-collect does not spell out that an index item should copy these fields from the execute receipt — one clarifying line, recorded not gated.

## Verdict

With run-2 (author-run execute/reclaim), the reader (independent discovery/help/dependency-answer), and this chain (independent-seat real execute → attributable result → collect bound to the ORIGINAL execute correlation, honestly reporting the now-unavailable event range → guarded reclaim), #271's evidence set is complete for root's acceptance decision, with the cursor discrepancy corrected and both receipts preserved. Issue remains open until root rules.

---

# Regression run (2026-10-08) — full-range live collect, receipts bound

Dot's personal review kept the old chain PARTIAL (cursor-8 collect `event-range-unavailable`,
range_complete/failure_count/permission_count null; retained 0 is not PASS) and directed one
bounded real original-entry regression under the user's complete-issues authorization. The
bridge independently re-verified the full range and the stop before this binding.

## Receipts (stable locators, kept distinct from the old `/tmp/chain-*.json` set)

| Step | Fact | Receipt |
|---|---|---|
| execute | item `i271-entry-regression`, task `kpr-a-issue-271`, worker pool `codex/luna` (pool seat, not an Elite grant), session `codex-KPR-i271-entry-regression`, worker holder `af4426fd…`, prompt fp `sha256:723f0e5e…`; exec receipt's `dispatch_event_cursor` **7** copied verbatim into the index (no hand-built fields); dry-run validated first | `/tmp/r271-plan.json`, `/tmp/r271-execute.json`, `/tmp/r271-index.json` |
| attributable result | `/tmp/kpr-271-regression-result.md`: `./scripts/render-skills.py --check` exit 0 PASS (10 workers + kaola-project-runner + kaola-delegator + grok-bot host; budgets OK); `./scripts/validate.sh --suite test-issue-244-dispatch` exit 0, 80 tests OK; reply `REGRESSION-DONE <path>` | result file + `/tmp/r271-collect.json` excerpt |
| collect BEFORE stop, live session | `since: 7` (original execute cursor, as-is) → `through: 95` (turn_ended terminal), contiguous window, turn fingerprint matched, **`range_complete: true`**, **actual counts: failure_count 0, permission_count 0, pending 0**, no truncation, event_log_path recorded | `/tmp/r271-collect.json` |
| exact-stop AFTER collect | `stopped: true, exit 0, residual_pids: []` | `/tmp/r271-stop.json` |

## Old/new range distinction (both preserved)

- old `chain-collect5`: zero-width window (224, 224] — vacuous 0, withdrawn as range evidence (1cfe7d51→aa1c1444 correction);
- old `chain-collect6/7`: after stop → `event-range-unavailable`, counts honestly null;
- new `r271-collect`: live session, pre-stop, full original range (7, 95], `range_complete: true` with actual counts.

Mechanism boundary (demonstrated, no standard change): the complete range is obtainable only
while the seat is alive, before reclamation/log rotation; after stop the runner reports
`event-range-unavailable` instead of fabricating coverage.

## Navigation and manual cost (dispatch authoring, Host)

Skill body → issue-quoted collect contract → `kaola-dispatch.py --help` + `execute`/`collect`
subcommand help = 3 hops, 0 undocumented steps this run (old chain: 2 execute start refusals
without recorded reason + 1 undocumented diagnostic step). Manual supplements: one refused
state write (record-level `--expect-rev` vs file-level revision, corrected in the same turn)
and one dry-run before the real execute.

## Candidate identity (facts kept separate)

Working tree = commit `13a0e271` (local = origin/main) + the four protected dirty files
(`hosts/grok-bot/INSTALL.md`, `hosts/grok-bot/bridge.json`, `hosts/grok-bot/kaola-delegator.md`,
`templates/grok-bot/accepted-revision.json`; original ownership, NOT published by this binding)
+ known untracked docs/workflow paths. The worker's render PASS is the working-checkout
content-stage fact on that combined tree. The clean-origin "194 pin findings" figure carried in
earlier records is a stale, unremeasured number for this candidate — marked stale-unknown, not
re-tested in this run.

No source implementation changed in this binding. Issue #271 remains open awaiting dot's new
ruling on this receipt package.
