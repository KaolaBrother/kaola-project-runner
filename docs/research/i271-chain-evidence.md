# #271 real QA chain — complete evidence (2026-10-07)

The bounded gap named in the PARTIAL ruling, closed with real receipts:

1. **execute (real admission)**: item `i271-chain` on the Droid shared Elite grant (default/opus/core, count 1 — NOT the worker pool), holder `5e0b9cf369554e6ab702be68cbda0db8`, prompt fp `sha256:388312cc…`, repo = this KPR repo, dispatcher = this Host. Exec receipt `/tmp/chain-exec.json`.
2. **Attributable non-empty result**: `/tmp/kpr-271-chain-result.md` (541 B, 3 original sentences — including a genuine undocumented-step finding below).
3. **collect by ORIGINAL correlation** (exit 0, `/tmp/chain-collect5.json`): bound via the execute receipt's own session/holder/prompt-fingerprint/repo/cursor; outcome `turn_completed`, stop_reason `end_turn`, unknown_reasons `[]`, failure_count 0, permission_count 0. Read-only turn view (`--item`), index file byte-identical after.
4. **Tool exact-stop + residual**: guarded stop with the full holder id → `stopped: true, exit 0, residual_pids []`.

## Genuine undocumented-step finding (from the chain worker + the collect authoring)

The collect `--item` turn view requires the index item to carry `dispatch_event_cursor` (int) and `prompt_fingerprint` — and the item-level `repo` must match the envelope repo. Building the index from the execute receipt needed three corrections (`event_cursor`→`dispatch_event_cursor`; `prompt_sha256`→`prompt_fingerprint`; missing item `repo`), each surfaced as a `dispatch-binding-missing` refusal until fixed. The refusal was typed and honest each time; the field names/requirements are documented nowhere a fresh reader would find them (dispatch-collect lists the flags, not the index item schema). Candidate doc improvement: one line naming the index item's required binding fields. Recorded, not gated.

## Verdict

With run-2 (author-run execute/reclaim), the reader (independent discovery/help/dependency-answer), and this chain (independent-seat real execute → attributable result → correlated collect → guarded reclaim), #271's evidence set is complete for root's acceptance decision. Issue remains open until root rules.
