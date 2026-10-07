# Release candidate 2026-10-08 — evidence pack (dot/root readable)

EVIDENCE commits (this directory, on `main`) are strictly separate from the CANDIDATE commits
under review; nothing here changes the reviewed P2 tree or its pin binding.

## Candidate (fixed, under review)

- Branch `release-candidate-2026-10-08` pushed to origin at **P2 = `57550098`**
  (`5755009824357d718e5fbc2906e5a8545803c6e7`), naming content commit **R2 = `6ca79623`**
  (`6ca79623d9ca4aaf48b05e67a9e96145cc8808de`).
- Lineage: `48d023a4` (origin/main) → R1 `a6af2d88` (four protected grok-bot content files,
  owner-staged verbatim; byte-identity to main's dirty four verified by Fable) → R2 `6ca79623`
  (three contract-test alignments, +13/−5) → P2 `57550098` (label pin; delta vs R2 exactly the
  four pin paths). R1/P1 `a6af2d88`/`65531ff4` superseded, kept in history.
- Diffs for dot's read: `git diff a6af2d88 6ca79623` (the three test corrections),
  `git diff 6ca79623 57550098` (the four pin paths), `git diff 48d023a4 a6af2d88` (protected
  four as committed).

## QA chain (all true exits; see MANIFEST.sha256)

| Tree | Check | Exit | File |
|---|---|---|---|
| working (48d023a4 + protected dirty) | full inventory | 1 (3 FAILED, originals preserved) | `rqa-working-validate-full.log` |
| clean 48d023a4 | render --check | 1 (207 pin findings) | `rqa-clean-render.log` |
| clean 48d023a4 | validate.sh | 1 (pin gate, 0 suites) | `rqa-clean-validate.log` |
| R1 a6af2d88 | render --check | 0 | `rqa-R-render.log` |
| P1 65531ff4 | full inventory | 1 (3 FAILED + 244, see below) | `rqa-P-validate-full.log` |
| P1 65531ff4 | 244 sequential | 0 (80 tests OK) | `rqa-P-244-recheck.log` |
| **P2 57550098** | full inventory (serial) | **0** (0 FAILED; 94-entry map) | `rqa-P2-validate-full.log`, `rqa-P2-suite-map.txt` |
| P2 57550098 | render --check --require-pinned | 0 | `rqa-P2-require-pinned.log` |

94-entry suite map = 92 `.py` suites ok + 2 `.sh` acceptance PASS (`test-installer-migration.sh`,
`test-installer-runtimes.sh`); the 74 `Ran N tests` lines are unittest reports (1539 tests), not
the suite count. The P1 244 failure (`foreign capture`, subTest with 1s runner timeout) did not
reproduce sequentially on the same tree; Fable qualified the contamination attribution as
plausible-not-strictly-proven — recorded as such, non-blocking.

## Fable final review (standing thinking scope, shared claude-code seat)

- Dispatch: `rfable-plan.json` / `rfable-execute.json` (execute receipt: worker holder
  `5d9d225878f599572305f7ee66b90198`, prompt fp `sha256:fe8bd111bc43…`, original cursor 14);
  live pre-stop collect `rfable-collect.json` (`range_complete: true`, since 14 → through 42,
  0 failures / 0 permissions); exact stop `rfable-stop.json` (residual `[]`, exit 0).
- Review full text: `kpr-fable-final-review.md` (sha256 `eb14eaab…`) — tree identity verified
  (7-file total delta vs main; protected four byte-identical), 1a/1b/1c **CONFIRMED**, QA chain
  **CONFIRMED** (one qualified attribution), gaps: (1) branch ref was stale at P1 — fixed by
  pushing the branch at P2; (2) 244 contamination plausible-not-proven (non-blocking);
  (3) 1c could be `assertIs(..., False)` (non-blocking). **`FINAL: PASS`**.
- Brief given to the reviewer: `kpr-fable-final-review-brief.md`.

## Boundary

Publish, tag, install and consumer adoption remain BLOCKED until root's personal review (dot
arranges) passes on the SAME candidate `57550098`. Main's four protected files stay dirty and
owner-owned; no KW changes; no new issues; no architecture.
