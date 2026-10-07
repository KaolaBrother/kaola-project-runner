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
