# Finalization summary — issue #275 (Migration P1 slice 1: baseline correction + residuals + characterization contracts)

## Delivered

Slice 1 of #275. **No code motion:** `scripts/kaola-acp.py`, `scripts/kaola-acp-holder.py`, `scripts/kaola-dispatch.py` and every other script are untouched (they are changed by in-flight #278/#286/#287; the extraction starts only after those merge, on Host direction).

- `docs/designs/modular-core-2026-10-07/migration.md` — P1 acceptance now names the **721-node AST inventory (top 522 / nested 199)** and the measured source baseline **origin/main `60e9e717`**, and states the baseline is refreshed after #278/#286/#287 merge with no full-inventory audit precondition. A baseline receipt records the recount mismatch instead of rewriting expectations.
- `docs/designs/modular-core-2026-10-07/inventory-matrix.json` — the 18 explicit keep-in-place rows **adopted keep-in-place** with a one-line reason each; **`parse_flat_yaml` rebound `C5-dispatch` → `C2-acp-adapters`**; **`line_size` stays `C3-events`**. No other row reassigned.
- `docs/designs/modular-core-2026-10-07/inventory-appendix.md` — the same 20 rows marked in place plus a "P1 residual decisions" section; `inventory-matrix.json` named authoritative.
- `tests/contract/test-issue-275-core-contracts.py` — characterization contracts for the decided CORE surfaces against the CURRENT code: identity/version facts; the DUAL process facts (`kaola-acp-holder.py` `process_alive`/`libproc_ps` vs `kaola-acp.py` `pid_alive`/`libproc_ps`, the `PermissionError→True` branch, the unreadable-argv fixture, the type-guard divergence **recorded and left as the named P1 decision input — no variant picked**); atomic state write (temp file + `os.replace`; failure leaves the original); and an import-graph recording skeleton.
- `scripts/validate.sh` — the suite registered in `python_suites_all` and exactly one lane (`python_suites_a`).

## Candidate

- Branch `workflow/bundle-275`.
- Host accepted `4fad39e205a7df9a888b886b0e17afa21ebc977c` (base `60e9e717`).
- Rebased onto `origin/main` `21ec9a37` (#277 P4, with #281/#282/#283/#285 merged). The only conflict was `scripts/validate.sh`, and it was mechanical: both sides appended suites after `test-issue-264-validate-lane-integrity.py`. Resolution keeps main's `test-ddd-pack.py` + `test-issue-277-kw-readonly-index.py` and this run's `test-issue-275-core-contracts.py`; the whole inventory was then verified to be a strict partition (all=90, lane A=39, lane B=51, no duplicate in any array, none in both lanes, none missing a lane).
- Implementation commit after the rebase: **`efeaf91a`**.

## Evidence locations

- `python3 docs/designs/modular-core-2026-10-07/recount.py` at `60e9e717` and again at `21ec9a37`: **exit 1**, `TOTAL: top 523, nested 199, all 722`; `MISMATCH kaola-acp-holder.py (51,158,209,7bc65d5d…) expected f455cd27…` and `MISMATCH kaola-acp.py (196,12,208,e016b255…) expected (195,12,207,d957f86e…)`. Cause: #278 added `session_directory` (top 195→196) and changed holder bytes. `kaola-dispatch.py` (`64fcb90de126a684`) and `kaola-record-contract.py` (`b5b61d8fdf4f30de`) still match. Recorded, not rewritten.
- `python3 tests/contract/test-issue-275-core-contracts.py` after the rebase: **Ran 20 tests, OK** (`/tmp/i275_v2.log`).
- `python3 tests/contract/test-issue-264-validate-lane-integrity.py` after the rebase: **Ran 4 tests, OK** (`/tmp/i264_v2.log`).
- Mutation-oracle sweep on the accepted candidate: **22/22 deliberately broken expectations bit**, all reverted; residue grep empty; the restored file ran 20 OK (`/tmp/i275_mutations.log`).
- `.cache/final-validation.md` — recorded validation for the two direct suite commands, verdict pass.

## Known failures or unverified scope

- `./scripts/validate.sh --suite test-issue-275-core-contracts.py` stops at the inherited stale protected Grok Bot pin (`3de9f61afbfa`) during the required `render-check`; the suite body never runs through validate.sh. Direct `python3 tests/contract/test-issue-275-core-contracts.py` is the passing evidence. This run did not edit the pin.
- The DUAL process-facts implementation is intentionally left unresolved in this slice; the cut after #278/#286/#287 merge picks one variant and keeps the `PermissionError→True` + "unreadable frees nothing" semantics.
- #275 stays **OPEN**: this is slice 1 only (internal cut + contract tests first); the code-motion slices remain.

## Validation

classification: final_validation_stale
green: false
mode: final-validation

recorded validated_candidate_hash "816cb27299e22024ee5bfb4c8e7d3f265341dce76f80eddaeffb77357d1640b0" != current code-tree hash "4407cec35ea9619bfabe0aad1af349a9833aacbdb8739437932eef5537a4dcfd" — a relevant source/test/test-consumed file changed after the recorded validation; re-run the validation command and re-record final-validation.md with a fresh hash

A relevant source/test/test-consumed file changed after validation — or the record was written from a different checkout than this one. Re-run the validation command, then re-record with `kaola-workflow-validation-runner.js record --project <project> --verdict pass --command "<the validation command you ran>"`, invoked from the working tree you validated (the gate hashes the tree its own shell is in, and a linked worktree and main differ until the branch merges); never hand-patch the hash.

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- docs/designs/modular-core-2026-10-07/inventory-appendix.md
- docs/designs/modular-core-2026-10-07/inventory-matrix.json
- docs/designs/modular-core-2026-10-07/migration.md
- scripts/validate.sh
- tests/contract/test-issue-275-core-contracts.py

## Follow-Up Items

- None filed. The stale protected pin is a pre-existing reported condition; this run did not file or modify it. #275 remains open for the code-motion slices.

## Readiness

Host acceptance of `4fad39e2` stands and the rebased candidate `efeaf91a` reproduces the same 20-test / 4-test direct results with the doc bytes unchanged. The recount mismatch is recorded rather than silenced. #275 is intentionally kept open; this run is review/merge ready for slice 1 only.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-codex-160-live-2026-10-03.md
- docs/harness-acp-compat-2026-10-01.md
- docs/harness-acp-compat-2026-10-03.md
- docs/harness-acp-compat-2026-10-06.md
- docs/harness-acp-reverify-2026-10-01.md

