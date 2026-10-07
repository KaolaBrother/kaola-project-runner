# KPR release candidate 2026-10-08 — Fable read-only final review brief

You are reviewing the FIXED release candidate tree. Thinking/review only: you write exactly one
file, `/tmp/kpr-fable-final-review.md`, and touch nothing else. Read-only on all repositories.

## Exact tree under review

- Candidate worktree: `/tmp/kpr-release-candidate`, branch `release-candidate-2026-10-08`,
  **pin commit P2 = `57550098…` (HEAD), naming content commit R2 = `6ca79623…`**.
- Lineage: `48d023a4` (origin/main) → R1 `a6af2d88` (four protected grok-bot content-stage
  files, owner-staged verbatim) → R2 `6ca79623` (three contract-test alignments) → P2 `57550098`
  (label pin, delta vs R2 exactly the four pin paths). R1/P1 (`a6af2d88`/`65531ff4`) superseded.
- The four protected files in the MAIN checkout remain dirty, uncommitted, owner-owned; the
  candidate carries the same content committed (R1). Main stays at `48d023a4`.

## What to verify (adjudicate each; cite file:line and commit)

1. **Three test corrections in R2 `6ca79623`** — each was applied ONLY on a wrong-oracle /
   stale-fixture proof against an already-merged contract. Confirm or refute each proof:
   a. `tests/contract/test-progressive-disclosure.py` expected control-plane script list now
      includes `kaola-compact-recovery.py`. Contract source: #274 merged `93662173` ships the
      helper and its closure suite FAILS packages lacking it; the old enumeration was last
      touched at `848e2804`, a proven ancestor of `93662173`. Is the updated enumeration
      faithful (helper is not a transport script; exclusion semantics kept)?
   b. `tests/contract/test-issue-162-upgrade-safety.py` drain-restart fixture now nests a
      private 4-level record root. Contract source: #278 merged
      `scripts/kaola-acp-paths.py::check_record_root` (private caller-owned write root); the
      old stub's shallow `self.root` made `parent^3` resolve to `/`, correctly refused.
   c. `tests/contract/test-issue-187-delegator-any-host.py` non-zcode attestation assertion
      changed from `assertNotIn("acp_holder_alive", session)` to `assertIsNot(..., True)`.
      Contract source: #278 merged CHANGELOG: "Locator worker session presence now reads ACP
      records for all ten platforms." The invariant preserved: never claim alive without a
      live record. Was any real assertion deleted or any threshold loosened? (None claimed.)
2. **QA receipts** (verify the logs exist and the exits are as stated; do not re-run the full
   inventory): working full `exit 1` (`/tmp/rqa-working-validate-full.log`, the three original
   failures preserved); clean `48d023a4` render `exit 1` with 207 pin findings
   (`/tmp/rqa-clean-render.log`); P1 full `exit 1` incl. a 244 `foreign capture` failure later
   proven concurrent-run contamination (`/tmp/rqa-P-244-recheck.log` = 80 OK sequential);
   **P2 full `exit 0`** (`/tmp/rqa-P2-validate-full.log`; exact 94-entry map:
   `/tmp/rqa-P2-suite-map.txt` — 92 .py suites ok + 2 .sh acceptance PASS; the 74 "Ran N
   tests" lines are unittest reports, NOT the suite count; 1539 tests total across reports);
   pin gate `/tmp/rqa-P2-require-pinned.log` exit 0.
3. **Release boundary integrity**: P2 uses a pre-release LABEL (no version claim); publish,
   install, tag and consumer adoption are BLOCKED until root + Fable both pass; the four
   protected originals in main are untouched; no KW changes; no new issues; no architecture.

## Deliverable

Write `/tmp/kpr-fable-final-review.md`: per-item verdict (CONFIRMED / REFUTED with evidence),
any gap you find in the candidate or the QA chain, and one final line
`FINAL: PASS` or `FINAL: FAIL — <reason>`. Reply in-chat with exactly:
`FABLE-REVIEW-DONE /tmp/kpr-fable-final-review.md`. Nothing else.
