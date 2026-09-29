# Finalization Summary — issue-236 (correction run)

## Delivered

Outer final audit corrections 1-4 for issue #236, applied Host-direct on top of the
accepted delivery (candidate commit 6f1e4cca, branch workflow/issue-236):

1. Synthetic test engine removed: `tests/contract/test-issue-236-install-completion.py`
   reduced from 350 to 97 lines. The `completion_row` decision engine, invented-outcome
   fixture rows, and broad text-phrase assertions are gone. Retained coverage: the actual
   documented DSH inspection command from `docs/api.md` executed against an isolated
   fixture (real package resolution), and the Codex pinned pair checked against the
   archived #226 finalization summary (reused evidence, no live probe). Installer footer
   behavior tests remain in `tests/contract/test-installer-runtimes.sh` (real installer
   runs, unedited this round — previous PASS reused).
2. Normal content-stage transition: `templates/grok-bot/accepted-revision.json` now
   `stage: content` (no commit/release/label). Published v0.6.11 R/P/tag untouched in
   history; installed live seats untouched. `render-skills.py --write` and `--check`
   both exit 0; all generated files restored through the renderer (bridge carries the
   honest unpinned placeholder, not saveable).
3. `docs/api.md` absent/unknown semantics corrected: absent unrequested runtimes are
   outside required preparation (`skipped: absent`, not an obligation to install
   everything, not a completeness blocker); an explicitly requested missing runtime is a
   distinct `not-ready: absent` row with exact recovery; unresolved `unknown` is a
   distinct row whose concrete resolution is rerunning the existing survey in the correct
   bound-target launch environment (login shell, PATH, manifest binary override) before
   deciding absence. Override resolution and no-login preserved.
4. Grok Bot template: the unrelated pre-release UAT sentence and the owned locator-link
   recovery instruction are restored (concisely); the new routing text was shortened
   instead, keeping one canonical anchor link. Rendered guide 8130/8192 bytes, verified
   through the renderer.

## Candidate

- Correction commit: 6f1e4cca (workflow/issue-236), on top of merged 671f933c / ce0c4062.
- Validated candidate hash: bafbba37fc840d3bf8c5458fff4221af9d24c47969e73d6c47cf9baa8bb60986
  (bound to the worktree by the recorded validation).

## Evidence

- `.cache/final-validation.md`: verdict pass for
  `bash -c './scripts/render-skills.py --check && python3 tests/contract/test-issue-236-install-completion.py'`
  (render --check PASS incl. budgets; 2 tests OK) run from the candidate worktree.
- Reused, still-valid evidence: `tests/contract/test-installer-runtimes.sh` PASS and
  `tests/contract/test-installer-migration.sh` PASS from the accepted delivery round
  (files unedited by this correction; no changed bytes to invalidate).

## Known failures / unverified scope

- None for this correction scope. The former render --check pin-gate failure is resolved
  by the content-stage transition, not by label: the gate now passes with actual output.
- Out of scope (unchanged): no release, no tag, no CHANGELOG release section, no pin
  machinery change, no broad runtime reinstall, no live ACP upgrade (DSH 0.1.5-rc.3 vs
  verified 0.1.7-rc.2 and PATH codex 0.157.1 vs pinned pair remain documented follow-through
  facts for the installed-preparation procedure this issue delivers).

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- docs/api.md
- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- templates/grok-bot/INSTALL.md.tmpl
- templates/grok-bot/accepted-revision.json
- tests/contract/test-issue-236-install-completion.py

## Follow-Up Items

- None filed: the audit corrections are recorded on issue #236 itself (reopen comment);
  no run-discovered defect beyond them.

## Readiness

Final readiness: complete for the audited correction scope; issue #236 closes on merge.

## Sink Findings

post_rebase_tests: skipped
