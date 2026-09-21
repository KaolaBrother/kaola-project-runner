# Finalization summary — issue-123

## Delivered
Reference-counted shared blocks (Issue #123, per the Yanlei ruling and Fable review): a runtime installs or uninstalls alone without deleting, shadowing, or blocking what another runtime still uses.
- Skill receipts carry `referrers`; same build → `refer`, other build → in-place `update` keeping referrers; uninstall/absent withdraw only this runtime's reference (`kept`) and delete only when none remain; `--method link` writes a receipt; pre-ledger receipt = every runtime mapped to that root (fail-closed).
- `~/.local/bin` kaola-acp / kaola-acp-holder / kaola-project-runner-locate share one sidecar ledger `.kaola-project-runner-bin-links.json` ({runtime, checkout}); usable existing link → referenced instead of `refusing ... exit 1`; dangling still refused; uninstall keeps a link while another referrer or the Grok Bot locator registration receipt exists; the registration receipt is never written.
- #105 skew scan scope unchanged.

## Files Changed
scripts/install-local.sh, scripts/validate.sh, tests/contract/test-issue-123-shared-refs.py (new), tests/contract/test-installer-runtimes.sh, README.md, CHANGELOG.md, docs/api.md, docs/architecture.md, docs/grok-bot-host.md, templates/orchestrator/references/host-startup.md.tmpl, skills/kaola-project-runner/references/host-startup.md (rendered).
Commits (rebased onto 5f4f40c): bb30e6e feat, 3738804 test, 98deeb3 docs.

## Test Coverage
test-issue-123-shared-refs.py — 6/6 tests, 58 checks (shadow HOME only): T-a1 order-independent refer; T-a2 one-sided uninstall both directions with the remaining runtime's start/observe/send/capture/stop via its installed Skill (fake ACP agent); T-a3 older build updated in place, referrers kept, #105 alignment skew 0, dsh Host start not refused; T-c1 usable link referred / dangling refused pre-write; T-c2 kept while another checkout or the locator registration refers, removed with the last referrer; T-b1 install roots ⊂ #105 scan roots. Baseline installer (fe7c806) fails 5/6 (T-b1 pins unchanged scope). test-installer-runtimes.sh updated for the three ruling-changed behaviors.

## Validation
- `python3 scripts/render-skills.py --check && ./scripts/validate.sh` on 98deeb3: render PASS, validate rc=0 (kaola-workflow/issue-123/evidence/validate-rebased.log; installer-runtimes/migration PASS; sweep residual_pids []). Pre-rebase run on a1d47ea also rc=0 (evidence/validate.log).
- run-chains: chains_config_missing (consumer repo) — gate is .cache/final-validation.md, validated_candidate_hash 537563b6a220…
- Acceptance: Host (Project Runner) ACCEPTED candidate a1d47ea 2026-09-21; rebase changed only a CHANGELOG additive conflict, re-validated.

## Changed Paths
Finalize check (source-scoped; docs/README/CHANGELOG are in the commits but outside this list):
scripts/install-local.sh, scripts/validate.sh, skills/kaola-project-runner/references/host-startup.md, templates/orchestrator/references/host-startup.md.tmpl, tests/contract/test-installer-runtimes.sh, tests/contract/test-issue-123-shared-refs.py

## Issue walk (#123 ② acceptance)
1. Per-runtime uninstall contrast — fixture-level for kimi-cli⇄dsh (T-a2) and codex bin links (T-c1/T-c2); the live real-machine matrix was NOT executed (dispatch forbade touching real user roots); Host accepted this disclosure.
2. kimi-cli/dsh shared root by reference — T-a1, T-a2, T-a3.
3. ~/.local/bin three links by reference incl. locator — T-c1, T-c2.
4. #105 scope unchanged — T-b1 + existing #105/#119 suites; S6 extra roots (Kimi `<KIMI_CODE_HOME>/skills`, dsh `${DSH_HOME}/skills`) not added pending live E2 — Host ruled no follow-up needed (consistent with "no forced exclusive root").
5. Docs — see .cache/doc-docking.md (DOCKED).
6. render --check and validate.sh — PASS.

## Documentation Docking
DOCKED — .cache/doc-docking.md.

## Follow-Up Items
None filed. Unexecuted, disclosed: live per-runtime uninstall matrix; S6 root live verification (Host: not needed); no independent code review (Host accepted).

## Readiness
READY — accepted, validated on the rebased candidate, docs docked.

## Sink race addendum (2026-09-22)
The first merge sink stopped cleanly with "FF merge failed": #122 sank to main (fd909e1) mid-sink and the sink's re-rebase conflicted. Branch and main were left intact. Rebased workflow/issue-123 onto fd909e1 by hand; the only conflict was the same additive CHANGELOG Unreleased case (#122's entry kept beside #123's). host-startup.md.tmpl and docs/api.md merged automatically and were checked. New tip 4b346bd (21a29eb feat, d807ef5 test, 4b346bd docs). Re-validated: render --check PASS, validate.sh rc=0 (evidence/validate-rebased-fd909e1.log; test-issue-123 6/6 58 checks, test-issue-119 9/9, residual_pids []).

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-123/.cache/doc-docking.md
- kaola-workflow/archive/issue-123/.cache/final-validation.md
- kaola-workflow/archive/issue-123/.cache/mirror-digest.json
- kaola-workflow/archive/issue-123/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-123/finalization-summary.md
- kaola-workflow/archive/issue-123/mission-list.md
- kaola-workflow/archive/issue-123/workflow-state.md
