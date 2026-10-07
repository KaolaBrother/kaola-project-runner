# #273 / #274 independent acceptance review — Host read-review (2026-10-07)

Scope: what is VERIFIED vs what remains (main-unreleased / consumers-not-adopted), for root's ruling. No release or install actions taken; the root release/install gate is untouched.

## #273 — PID-reuse agent_alive misreport (list path)

**Verified (real evidence):**
- Fix at `5cef759a` (origin/main): list projects `agent_alive` ONLY from a verified holder's type-checked `state_reply`; unreachable+argv-anchor-false → mismatch; all else null (unknown ≠ dead); no release/stop keyed off it; no new taxonomy/gate/record fields; reuses holder_identity + holder_argv_anchor.
- Real-entry suite `test-issue-273-list-identity.py` (9 tests, EXIT=0 via `validate.sh --suite`): production list CLI + controlled holder sockets (verified true/false/non-bool/missing; dead excluded/null with --include-dead; live-unrelated mismatch/null; silent unreachable/null; persisted-None stays unknown; STATE-input bytes unchanged; negative control). Non-vacuous after `e7aea057`.
- Independent QA originals: bridge 8/8 real-entry (negative control 6/8 fail on HEAD~fix) + 6/6 real consumer (delegator_seats→seat_projection: null/false keep the seat occupied; unknown never releases; stopped excluded). resolve_send_wait is NOT treated as a list consumer (bridge C1 correction honored).

**Not yet done (boundary, not defect):** status-path verification remains a named open item (bridge-narrowed title). **Main is NOT released**: no tag after v0.9.1 carries the fix. **Consumers have NOT adopted it**: accepted/install roots still hold the pre-fix builds (no `kaola-compact-recovery.py` helper in any installed root; installed orchestrator copies predate `5cef759a`). Dev-side leak note: this session's renders wrote the post-fix build into the local `~/.zcode`/`~/.agents` skill copies (7cbde08d) — an isolation artifact of developing in the canonical repo, NOT a consumer adoption; the accepted checkout (kaola-project-runner-accepted @3de9f61) is untouched.

**Acceptance conclusion (for root):** the list-path defect is fixed and tested on real entries, with independent bridge QA. Residual scope: status-path verification + the release/install boundary (root's gate). Recommend: close #273 for the list path on root's read; track status-path as the named remainder (issue #273 body already scopes it).

## #274 — package closure (kaola-compact-recovery.py)

**Verified:** render fix at `93662173` (origin/main) copies the helper into `skills/kaola-project-runner/scripts/` (dispatch loads it from its own dir); suite `test-issue-274-package-closure.py` (4 tests, EXIT=0; bridge independently executed 4/4): isolated-package POSITIVE recovery-input (real #255 signal shape: completed/session-bound/host-role → exit 0/written), helper-removal fails NAMING the dependency (FileNotFoundError, not signal-unverified), foreign-session/non-host/unfinished guards refuse signal-unverified with state bytes unchanged, no repo-root/sibling fallback. Both lanes + replay registered.

**Not yet done:** same boundary — no release tag carries the closure; installed roots lack the helper (verified: no installed root has it). Consumer post-compaction maintenance remains exposed until the next release+install cycle (that is the release boundary's job, not a defect in the fix).

**Acceptance conclusion (for root):** the packaging defect is fixed, tested (positive + dependency-named negative + guards), and independently executed by the bridge. The issue can close on the shipped-to-main fix; consumer protection completes at the next release/install boundary that root authorizes.

## 272 note (scope honesty)

The #272 loop-execution evidence stands on its own findings (F1 text/suite-scoped, F2/F3 bridge-executed QA). The NEW AI correction relayed by the parent is recorded as RELAY ONLY — original AI-bridge artifacts were not read this round; no completeness claim is made for it here.
