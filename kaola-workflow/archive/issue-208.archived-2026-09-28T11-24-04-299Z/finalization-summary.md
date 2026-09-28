# Finalization Summary — Issue #208 (second archive: reopened QA-finding scope)

This is the **second** finalize/archive transaction for issue #208. The first
(`kaola-workflow/archive/issue-208.archived-*` history — see the sibling first-run records) closed
the original consolidation run at `ea856048`. Issue #208 was then **reopened** by the Host's final
cross-surface QA read, which recorded exactly one bounded defect (comment `5868496390`). This second
transaction covers only that reopened scope. Both archives are kept; neither overwrites the other.

## Delivered

Fixed the single stale README sentence that contradicted the lifecycle-once semantics this issue
already landed in the first transaction.

- Candidate: `52bf5abf` on `workflow/issue-208` (base `68e6e2ef`, no re-sync needed — `origin/main`
  was still `68e6e2ef` at finalize time).
- Host accepted the delivery after directly verifying the diff (one file, 2 insertions / 1 deletion).

### Issue walk (reopened scope, comment 5868496390)

The reopen comment's sole finding: `README.md` ~line 392 said *"stop each seat once its delivery is
accepted"*, contradicting the merged lifecycle-once semantics (acceptance authorizes the pending
finalize; the seat is retained until its finalize/cleanup duties finish or ownership is handed off,
then exact-stopped — main Skill step 5).

**Satisfied.** `README.md` line 392 now reads:

> cap, and an accepted seat keeps only the finalize/cleanup duties it owns until it
> owns none or is abandoned, when it is exact-stopped; give a new task a new
> session; idle is not keep-alive.

This matches `templates/orchestrator/SKILL.md.tmpl` step 5's canonical wording (acceptance
authorizes pending finalize; keep only owned finalize/cleanup duties; exact-stop once none remain or
the seat is abandoned) while preserving the surrounding Elite-preset authorization facts
(stop-before-start at the cap, new task → new session, idle is not keep-alive).

**Residue sweep.** The README was grepped for any other same-meaning instance (`stop each seat`,
`once its delivery is accepted`, `seat once`, and equivalents): **no other instance**. The only
near-hit, `host-startup.md.tmpl:121` ("whose delivery is accepted or abandoned → stop, prove gone"),
carries a different and correct meaning (stop condition for a dead/errored seat) and was
deliberately left untouched. Nothing outside this one sentence was changed.

## Files Changed

- `README.md` — the Elite-preset authorization bullet, one sentence rewritten (2 insertions, 1
  deletion). No other path changed: `render-skills.py --write` produced no byte change, and
  `git show --stat 52bf5abf` is `README.md | 3 ++-`.

No template, generated surface, test, CHANGELOG, or docs file was touched. No release, tag, or
install.

## Test Coverage

- `./scripts/render-skills.py --write` → `WROTE (10 workers + kaola-project-runner +
  kaola-delegator + grok-bot host … budgets OK)`; generated surfaces were already current.
- `./scripts/render-skills.py --check` → `PASS (… budgets OK)`, exit 0.
- Pin check: the existing README assertion in `tests/contract/test-issue-118-seat-cap.py`
  (`authorized count … hard cap on live worker processes … stop-before-start`) was re-run against
  the new text and still matches. **No stale pin exists, so no test was edited.**
- `tests/contract/test-issue-118-seat-cap.py` → 18 tests OK (includes
  `test_stop_in_same_beat_after_acceptance`, which asserts the main Skill / zcode-host surfaces —
  untouched and still green).
- `tests/contract/test-issue-88-permission-defaults.py` → 42 tests OK (asserts README
  permission/platform facts — unaffected by the wording change).
- `./scripts/validate.sh` → **exit 0, 49 suites, zero failures**. The #209 failures cited in the
  first run's record did not reproduce on base `68e6e2ef`.
- No live model probe, release, tag, or install.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- README.md

## Documentation Docking

DOCKED — see `.cache/doc-docking.md`. The changed surface is `README.md` itself. `CHANGELOG.md` and
`docs/*` need no update: no user-visible behavior, CLI, transport, or API change, and no release in
this run. The two protected `docs/harness-acp-compat-2026-09-2{5,6}.md` files were not read, staged,
or copied.

## Follow-Up Items

- None opened by this run. The reopen comment's other observation (Worker-class "cheaper" wording;
  `worker-profiles` no longer statically listing all 20 rows) was already judged intentional per
  #211 class-guidance preservation and #214 installed-only design — not a defect, not re-opened.
- Issue #218 is implementing in parallel on snapshot/catalog surfaces; no overlap with this run's
  single README sentence. No conflict expected or observed.
- Both archive transactions for #208 are honest and distinct: the first covers the original
  consolidation design; this one covers the reopened one-sentence QA finding.

## Readiness

Delivered `52bf5abf`; Host-accepted; validation receipt `verdict: pass` bound to the candidate tree;
documentation docked; no deferred work. Ready to merge and close.
