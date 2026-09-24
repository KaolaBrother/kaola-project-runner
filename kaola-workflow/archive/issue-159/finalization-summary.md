# Finalization Summary — issue-159

Candidate: workflow/issue-159 @ 2c657580 (frozen; validated_candidate_hash
5032fafaa8d5647dba89769d666104a284f84f275a0fc35ea4387bc7edcf3da7)
Run posture: single-issue run on Mac Studio (droid delivery seat, session marker
s-44216-mufjkoxz); worktree .kw/worktrees/issue-159; sink=merge.

## Delivered

Issue #159 "install-local --runtime kimi-cli misses Kimi Code $KIMI_CODE_HOME/skills
(only writes ~/.agents/skills)" — Option A dual-install, exactly the authorized scope:

1. `scripts/install-local.sh` — `--runtime kimi-cli` now installs and uninstalls BOTH
   user-level roots (`~/.agents/skills`, shared with dsh, and
   `${KIMI_CODE_HOME:-$HOME/.kimi-code}/skills`, which moves with `$KIMI_CODE_HOME`),
   each with its own receipt set. The engine refactored into plan-every-destination
   then apply: a refusal in either root (generated Skill missing, foreign path,
   dangling bin link, malformed user hooks.json) still aborts the whole run before
   the first byte lands; the bin-link ledger stays primary-root-only; the Codex
   user-level compact hook stays Codex-destination-only. Uninstall withdraws the
   kimi-cli reference from every root it owns: the shared root keeps its Skills for
   dsh (`still referenced by dsh`), the kimi-specific root's Skills are removed (its
   only referrer). Pre-ledger receipts in each root keep legacy-referrer mapping
   (kimi-cli,dsh in the shared root; kimi-cli alone in the kimi root).
2. `scripts/kaola-acp.py` (+ every generated worker copy) — `HOST_SKILL_DISCOVERY_DIRS`
   for kimi-cli gains `.kimi-code/skills`, so the #105 worker/main build-skew Host
   gate scans both roots (Issue #119 line).
3. host-entry matrix (`templates/orchestrator/.../host-entry-matrix.md` + generated
   copy) and `docs/host-entry-evidence.md` — kimi-cli lists BOTH user roots with the
   Issue #119 lineage, the upstream skill-location docs (retrieved 2026-09-24), the
   fleet evidence from the issue's observed failure, the maintainer binary fact
   (Kimi Code 2.0.2), and a standing note that a dedicated live D3 for the added root
   stays a follow-up because it needs a real provider session.
4. Contract coverage —
   `tests/contract/test-installer-runtimes.sh`: kimi-cli dual-install into both roots
   under `$KIMI_CODE_HOME`, the referrers ledger covering both roots, dual uninstall,
   and the default root when `KIMI_CODE_HOME` is unset;
   `tests/contract/test-issue-123-shared-refs.py`: T-a1/T-a2 updated to the dual-root
   refer semantics (dsh stays in `.agents`; kimi root referred and fully withdrawn)
   and T-b1 asserts the kimi-specific root is a #105 scan root.
5. README.md and CHANGELOG.md (`## Unreleased`) — usage and behavior recorded.
6. Bridge stage: `templates/grok-bot/accepted-revision.json` returns to content stage
   (a74119a precedent; the v0.6.1 pin names the prior content commit) so render
   accepts post-pin work; bridge unpinned, `saveable: false`; no tag, no release.
   https://github.com/KaolaBrother/kaola-project-runner/issues/159

## Files Changed

33 files at 2c657580 vs base a4b6801, +422/−173: CHANGELOG.md, README.md,
docs/host-entry-evidence.md, scripts/install-local.sh, scripts/kaola-acp.py,
templates/grok-bot/accepted-revision.json,
templates/orchestrator/references/host-entry-matrix.md,
tests/contract/test-installer-runtimes.sh, tests/contract/test-issue-123-shared-refs.py,
plus the regenerated `skills/` (kaola-acp.py copies, main-skill-build.json, matrix copy)
and `hosts/grok-bot/` (bridge, manifest, guide) products of those inputs.

## Test Coverage

- `./scripts/render-skills.py --write`: WROTE rc=0 (first attempt rc=1 under the
  active v0.6.1 pin; resolved by the documented content-stage reset).
- `./scripts/render-skills.py --check`: PASS rc=0 (budgets OK, content stage, unpinned).
- `bash tests/contract/test-installer-runtimes.sh`: rc=0, PASS (kimi dual-root block).
- `python3 tests/contract/test-issue-123-shared-refs.py`: rc=0, 6/6 tests, 62 checks.
- `python3 tests/contract/test-issue-119-host-entry.py`: rc=0, 11/11 tests, 160 checks.
- `./scripts/validate.sh`: rc=0, zero FAILED/ERROR (named prerequisite skips only:
  bash≥4 watchdog lanes on bash 3.2.57, matching this machine's history).
- Live kimi-cli ACP smoke: PASS on real Kimi Code 2.0.2 (`~/.kimi-code/bin/kimi`,
  real persistent provider) — start `state=ready` with a real `acp_session_id`,
  observe `agent_alive=true`, one bounded send returned
  `final_text: "KPR159-live-smoke-ok"` (`stop_reason: end_turn`, 58 events),
  exact stop `residual_pids: []`, record-root sweep clean. Ambient dispatcher binding
  was scrubbed per validate.sh practice. Records under a scratch root; session logs
  under the established `~/.kimi-code/sessions`.
- Manual installer checks also run: dual uninstall of both roots; dsh coexistence
  (`.agents` kept after kimi uninstall with receipts `["dsh"]`); default
  `~/.kimi-code/skills` when `KIMI_CODE_HOME` unset; copy and link methods; reinstall
  no-op; a foreign directory in the kimi root refuses BEFORE `.agents` is written.

## Validation

The finalize transaction's own validation finding lands here at transaction time
(`kaola-workflow-claim.js finalize`); verdict recorded as `pass` via
`kaola-workflow-validation-runner.js record --project issue-159 --verdict pass`, receipt
`validated_candidate_hash 5032fafaa8d5647dba89769d666104a284f84f275a0fc35ea4387bc7edcf3da7`
in `kaola-workflow/issue-159/.cache/final-validation.md`, binding the frozen worktree tree.

## Changed Paths

The finalize transaction's own `changed_paths` report lands here at transaction time
(all paths this branch changed outside `kaola-workflow/` run state) — the 33-path list
above.

## Documentation Docking

DOCKED — `.cache/doc-docking.md`: CHANGELOG/README/evidence/matrix/scan updated in the
candidate; architecture/conventions/AGENTS no-impact reasons recorded; one stale
`docs/api.md` runtime table filed as follow-up #161 (P3, documentation) instead of
patching the frozen accepted candidate (bundle-153 → #155 precedence).

## Follow-Up Items

- filed: #161 (P3, documentation) — `docs/api.md` `--runtime` destination table still
  names only `$HOME/.agents/skills` for kimi-cli after #159's dual-root install, and
  the legacy-referrer note does not cover the kimi-specific root's kimi-only
  referrer; body non-empty, OPEN. `searched:` probe actually run — `rg -n -i
  'kimi.*skill|\.agents/skills|install-local|host-entry' docs/api.md` on the
  post-#159 tree: 4 hits, line 154 stale. Confirmed via `gh issue view 161`.
- Recorded review-seat minors (NOT fixed in this run, per Host direction): docs
  wording re-measured-vs-pending in matrix+CHANGELOG; duplicate-root uninstall rc=1
  edge case; missing second-root-refusal contract test.
- Standing (product) follow-up recorded in the evidence doc: dedicated live D3 for
  the kimi-specific root (real-CLI session, E1/E2 + negative control) needs a real
  provider session.

## Readiness

READY — Host acceptance granted for 2c657580 (review seat VERDICT: PASS, 0 blockers);
single-issue close; sink-merge into main, issue #159 closure with review-PASS evidence,
archive, and worktree cleanup proceed next. Issue #160 surface untouched; no release
tag, no pin commit, no version bump (accepted-revision.json stays content stage).

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-159/.cache/doc-docking.md
- kaola-workflow/archive/issue-159/.cache/final-validation.md
- kaola-workflow/archive/issue-159/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-159/finalization-summary.md
- kaola-workflow/archive/issue-159/mission-ledger.jsonl
- kaola-workflow/archive/issue-159/workflow-state.md
