# Finalization Summary — issue-333

## Delivered

Grok worker `grok-KPR-i333-dead-holder-retire` (grok/default) implemented the sanctioned retire
route for accepted tasks whose worker holder died, in commit `9e92da3a` on `workflow/issue-333`
(base = main `40162cda`).

- **`dead_holder_unknown_settlement()`**: an unknown dispatch row whose holder is proven dead
  (the three dead-holder causes: `event-range-unavailable`, `no-last-prompt`,
  `fingerprint-differs` without collected proof) may be retired when the task is `done` with an
  `accepted` verdict, an accepted per-item disposition, and the live row shows the session
  stopped or absent. Missing links, foreign holders and live sessions still refuse; every
  refusal names the route (`_DEAD_HOLDER_RETIRE_ROUTE`). No index bytes are written; a
  `fingerprint-differs` row that already carries collected continuation evidence stays on the
  older continuation route.
- **`collect` vs `status` discrepancy (verified, not a separate defect)**: `collect --item`
  classifies unknown because its event range is unavailable, while `status` can still report
  stopped-with-fingerprint from the record — the same close-path family, resolved by this route
  (retire no longer depends on collect's classification).
- Tests extend the already-registered `test-issue-286-retire-input.py` (+185 lines): the three
  dead-holder reasons retire with unchanged index bytes, absent live row, recorded stopped
  holder, explicit accepted disposition; refusals for missing link / foreign holder / live
  session / non-accepted disposition (naming the route); unrelated unknown and in-flight rows
  still refuse.

## Candidate

Branch `workflow/issue-333`, single commit `9e92da3a` over main `40162cda`.
Recorder-bound hash: `fb9a4da7f52ed444…`.

## Evidence

- Delegator reproduction (`.ka/repro333b.py`) rerun by the Host against both trees: worktree —
  all four cases (returned control + three unknown causes) retire, exit 0; main — the unknown
  cases still refuse `retire-unmet`. The reproduction is the regression test per the owner rule.
- Worker runs: 286 suite green; focused dispatch/state suites green; render PASS.
- Host runs on the exact candidate: **full inventory rc=0** (1294.7 s); render PASS; 286 suite
  OK.
- Validation record: `kaola-workflow/issue-333/.cache/final-validation.md` (verdict pass).

## Known failures and unverified scope

- No replay of the real dead KGIT i193 session through `collect --item` (the discrepancy was
  verified by source reading); the mock-based repro covers the classification contract.
- Worker-declared: full inventory was not run by the worker (the Host ran it on the candidate).

## Validation

classification: final_validation_stale
green: false
mode: final-validation

recorded validated_candidate_hash "fb9a4da7f52ed4448e818a1fe9d9f24f7e235b0764df113855c85811dc5f1f1a" != current code-tree hash "3a232b001bfb71bbdbb4252127cc6f55e3a48796d25b90a4b4f38dd32a963566" — a relevant source/test/test-consumed file changed after the recorded validation; re-run the validation command and re-record final-validation.md with a fresh hash

A relevant source/test/test-consumed file changed after validation — or the record was written from a different checkout than this one. Re-run the validation command, then re-record with `kaola-workflow-validation-runner.js record --project <project> --verdict pass --command "<the validation command you ran>"`, invoked from the working tree you validated (the gate hashes the tree its own shell is in, and a linked worktree and main differ until the branch merges); never hand-patch the hash.

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/ddd/packs/c4-state-retire.md
- docs/dispatch-collect.md
- scripts/kaola-dispatch.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- tests/contract/test-issue-286-retire-input.py

## Follow-Up Items

- None filed. Same family as #327 (obsolete-input retire) — this closes the dead-holder variant.

## Final readiness

Ready: candidate accepted (repro verified both sides + full inventory rc=0), validation
recorded pass, no tag/release/install performed.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-333/.cache/final-validation.md
- kaola-workflow/archive/issue-333/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-333/finalization-summary.md
- kaola-workflow/archive/issue-333/mission-ledger.jsonl
- kaola-workflow/archive/issue-333/workflow-state.md
