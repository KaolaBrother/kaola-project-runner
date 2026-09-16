# Issue #50 — independent review round 1 and orchestrator verdicts

Reviewer: clean-context `code-reviewer` (`review-50-r1`), read-only on the frozen candidate
`df8b85e..c1a9b91` in the bundle-50 worktree. Reviewer verdict: PASS-with-notes. Reviewer ran
`validate.sh` (exit 0), both #50 harnesses (10/10, 6/6), vendor vitest (130/130),
`kaola-dist.py --check` (byte-identical), `git diff --check df8b85e c1a9b91` (exit 2 → F1).
Full handback: session scratchpad `review-50-r1.md` (reproduced in substance below).

| # | severity | claim | orchestrator verdict | disposition |
|---|---|---|---|---|
| F1 | major | Acceptance "git diff --check clean" fails: the rendered `skills/…/vendor/claude-code-acp/dist/index.js` copy has 4 trailing-whitespace lines; the vendor `.gitattributes` does not cover the Skill copy; validate.sh never runs `diff --check`. | Confirmed (`git diff --check df8b85e c1a9b91` names lines 3059/3067/3077/3085). | Fixed: root `.gitattributes` exempts `skills/*/scripts/vendor/claude-code-acp/dist/index.js`; `validate.sh` now runs `git diff --check` and `--cached` when in a Git checkout. |
| F2 | minor | v0.4 block inserted inside the v0.3 list in `docs/runner-v2-dual-transport-design.md`. | Confirmed. | Fixed: block moved after v0.3 item 6. |
| F3 | minor | Bridge persists `~/.claude-code-acp/sessions.json` in live use; undocumented. | Confirmed (Runner sets no `CLAUDE_ACP_STATE_DIR`; the UAT left one entry there). | Fixed by documentation (README, docs/api.md: contents, override, role in `--continue`, rollback). Not relocated: `--continue` must see every Runner session on the machine. |
| F4 | minor | `sessions.json` read-modify-write has no atomic rename; concurrent bridges can read a torn file. | Confirmed by code read. | Fixed in the fork: temp file + `renameSync`; the read-merge window is documented as unlocked in UPSTREAM.md. Dist rebuilt byte-identically. |
| F5 | minor | If the holder SIGKILLs the bridge before its 2 s shutdown completes, a detached `claude` group could outlive it unseen by `residual_pids`. | Plausible by code read; not observed (graceful stop verified offline and live; `stop --force` not exercised live). | Recorded, no change: the holder's TERM grace (3 s) exceeds the bridge's own SIGTERM→SIGKILL window (2 s) on the graceful path. Carry as a known edge for a follow-up if `stop --force` residue is ever observed. |
| F6 | minor | The six other worker Skills are not byte-identical (shared `kaola-acp.py` copy changed, inert for them). | Confirmed; already recorded in Mission 2's result and CHANGELOG wording. | Recorded deviation from the issue text. |
| F7 | nit | `resolve_agent_command` did not reject `..`/absolute remainders. | Confirmed; only reachable from the checked-in manifest or the operator's own `--command`. | Fixed: token remainder must be relative with no `..`; otherwise `acp-bridge-missing`. Runner harness asserts two escape shapes. |
| F8 | nit | Upstream `cancelledSessions` flag can go stale if a cancel lands after the child closed but before `prompt()` returns; the fork's rethrow (agent.ts) would then misreport a genuine resume failure on the next turn as a cancel. | Plausible race, upstream-inherited; holder only forwards cancel while `turn.active`, narrowing it to the response-in-flight window. | Recorded, no change in this round. |
| F9 | unverified | `permit` is one-directional under this bridge (child has no stdin, no `--permission-prompt-tool`); the CLI's `permission_request` stream shape is only asserted by the fake. | Agreed; matches Mission 1 note (3) and the live UAT fact (no permission request emitted in bypassPermissions or manual mode). | Recorded in `uat-live-2026-09-16.md` and the Mission 3 result. |
| F10 | unverified | The default flip rests on a live UAT that is prose only in the diff. | The receipts were captured by the orchestrator during Mission 3 (`uat-live-2026-09-16.md` records the values; scratch receipt files were removed with the scratch repo). | Recorded; the Mission List and the UAT note are the run's evidence. |

Verified-OK areas per the reviewer (trust boundary, exact binary, holder env, bridge-missing refusal,
cancel/resume repair, per-turn flags, session store v2, provenance, fake fidelity) match the
orchestrator's own reading of the candidate.

Round 1 fixes commit: see Mission 4 result in `mission-list.md`. Mutation invalidates the reviewer's
PASS for the changed bytes (`scripts/kaola-acp.py`, `scripts/validate.sh`, `.gitattributes`,
`vendor/claude-code-acp/src/session-store.ts` + dist, docs); the re-run suite is the evidence for
those bytes.

# Round 2 — rebased candidate `46c7492` on `main` `4a705f3`

Reviewer: clean-context `code-reviewer` (`review-50-r2`), read-only. Verdict: PASS-with-notes,
four nits, nothing blocking. Verified: four commits `main..HEAD`, `db4b0d5` (P3) an ancestor;
`git diff main HEAD` for `scripts/kaola-acp.py`, `docs/api.md`, `CHANGELOG.md` equals the
pre-rebase delta `df8b85e..fa25281` except hunk offsets and CHANGELOG context; no lost,
duplicated, or reordered hunks; the content-stage flip is mandated by `pin_delta_findings`;
`render-skills.py --check` PASS; `git diff --check main HEAD` exit 0; grok-golden, orchestrator
template, worker template, and adapters unchanged; six non-Claude workers differ from main only
in `scripts/kaola-acp.py`; `validate.sh` exit 0; vitest 130/130; dist byte-identical; the round-1
fix bytes do what the commit claims. Full handback: session scratchpad `review-50-r2.md`.

| # | severity | claim | orchestrator verdict | disposition |
|---|---|---|---|---|
| N1 | nit | `validate.sh`'s `git diff --check`/`--cached` is vacuous on a clean checkout (pre-commit guard, not a check of the committed candidate). | Agreed. | Recorded; the committed range is checked by `git diff --check main HEAD` in the delivery evidence and by the reviewer. No extra mechanism added. |
| N2 | nit | The `scripts/../kaola-acp.py` escape shape in the Runner harness would pass without the fix (the file does not exist). | Confirmed. | Fixed: shape changed to `scripts/../scripts/kaola-acp.py`, which exists, so only the refusal satisfies the check. |
| N3 | nit | `session-store.ts` leaves the `.tmp` sibling behind if `renameSync` throws. | Agreed (error path only, logged). | Recorded, not changed: a fork rebuild would invalidate the live consistency evidence for a cosmetic error-path leftover. |
| N4 | nit | CHANGELOG says "Missions 1–3" and omits the Mission 4 fixes. | Confirmed. | Fixed in the changelog entry. |
