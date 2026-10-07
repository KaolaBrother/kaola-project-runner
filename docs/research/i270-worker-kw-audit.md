# KPR #270 audit — kaola-workflow writer-path claims

Repo audited: `/Users/ylmacstudio/Workspace/kaola-workflow` (read-only; no writes, no installs).

## Claim 1 — "each artifact has a single writer path in claim.js/sink scripts" — MISFIT

- `workflow-state.md`: **multiple writers across two scripts.** claim.js: `writeState`→`writeFile` at `scripts/kaola-workflow-claim.js:907` (callers :1292, :1734), `appendClosureBlock`→`writeFile` :2628, archive status stamp :2875, `writeFile(destState)` :4975, `writeFile(archiveState)` :6837. Plus `scripts/kaola-workflow-sink-pr.js:526` (`updateStateSinkBlock`→`writeFileAtomicReplace`).
- `finalization-summary.md`: **three writers.** claim.js `persistValidationToSummary` :4431 (writes :4404/:4427), archive-sanitize `writeFile(summaryPath)` :2894, sink-pr.js `appendSummary`→`fs.appendFileSync` :539 — plus the run's Agent authors the file itself.
- `final-validation.md`: agent-recorded (claim.js:4865 comment) **and** claim.js archive sanitize `writeFile(finalValPath)` :2908.
- Mission ledger `.ledger/issue-N.jsonl`: **primary writer is the Agent orchestrator, not a script** — claim.js:3547-3549 "the orchestrator writes the file itself". Script surface only mkdirs (`prepareMissionLedger` :3551), reference-writes (`writeMissionLedger` :3571, exported :7796), and moves it (`moveMissionLedger` :3084, called :3049).
- `.cache/chain-receipt.json`: single writer but in `scripts/kaola-workflow-run-chains.js` (`writeReceiptAtomic` ~:171-185) — outside the claim.js/sink set the claim names.

## Claim 2 — "sink transaction resumable/idempotent with named receipts" — FIT

- `scripts/kaola-workflow-sink-merge.js:1544` header "resumable step-receipt based merge pipeline"; `SINK_STEPS` :1560 (preflight, push_upstream, merge, finalize, stash_restore, archive_commit, push_main, closure); atomic `writeSinkReceipt` :1573-1576; resume loader `resolveSinkReceiptPath`/`loadOrInit` :1774-1858; idempotent step skip `if (receipt.steps[step] === 'done')` :2395 + `stepDone` :2374-2384; named journals `sink-receipt.json`/`sink-fallback.json` (:1253-1265); `disposeSinkJournals` :1584+; crash test hook `KAOLA_WORKFLOW_SINK_ABORT_AFTER` :1548. sink-pr.js is likewise re-entry-safe (:525 no-byte-change skip, :538-539 PR-URL dedup).

## Claim 3 — "no cross-artifact transaction spanning multiple files" — MISFIT

- Claim transaction: claim.js:1466 comment — "The transaction writes exactly two artifacts, the selection record and workflow-state.md" (plus `.ledger/` mkdir :3551).
- Finalize transaction (`finalize_transaction` ledger ~:4631) spans `mirrorFinalizationArtifacts` worktree↔main folder sync, archive move + `moveMissionLedger` :3049/:3084, `appendClosureBlock`, `persistValidationToSummary` :4884, and commits — multi-file by construction.
- The sink transaction itself mutates merge, archive folder, `workflow-state.md` mirror and `sink-receipt.json` in one resumable pipeline (:1560 step list).

## Claim 4 — "computeCodeTreeHash is the only code-tree hash implementation" — MISFIT

`computeCodeTreeHash` (`scripts/kaola-workflow-adaptive-schema.js:1124`, exported :2462; callers `run-chains.js:1180`, `validation-runner.js:1477`) is the canonical finalize-gate hash, but `computeLandableTreeDigest` (`scripts/kaola-workflow-validation-runner.js:554`, exported :1658, used :842) is a second code-tree digest over the same visibility band — deliberately different algorithm (NUL-joined Buffer-sorted records vs `'\n'` join), documented at `validation-runner.js:1167-1172`. Recording the wrong one yields `final_validation_stale`.

## Bottom line

Only claim 2 verifies. Claim 1 inverts reality (several artifacts are multi-writer; the ledger is agent-written). Claim 3 is refuted by two named multi-artifact transactions. Claim 4 misses `computeLandableTreeDigest`.
