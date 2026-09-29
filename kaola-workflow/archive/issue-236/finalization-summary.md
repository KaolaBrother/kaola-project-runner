# Finalization summary — issue #236

## Delivered

Installation now finishes through actual ACP preparation. README (default install, later examples, and the Grok Bot locator), `docs/grok-bot-host.md`, and the Grok Bot install/update guide (template and generated `hosts/grok-bot/INSTALL.md`) route completion through `docs/api.md#acp-layer-preparation-during-install`. That section states the ordered survey, payload verification, component resolution, authorized preparation, and bounded ACP check, plus the compact per-runtime row. `install-local.sh` prints the payload-versus-ACP footer only after a successful install, names the platform selection, and prints nothing of that kind on uninstall or failure. Exit codes are unchanged. `verify-install` remains a payload checker.

## Candidate

- Branch: `workflow/issue-236`
- Implementation commit: `671f933c9727f854ce16eee66a864e61c7539a7e`
- Host acceptance: PASS on that diff (7 tracked files +190/−59 plus `tests/contract/test-issue-236-install-completion.py`).

## Evidence locations

- Host acceptance in this session, including the independent rerun of the installer tests, the issue-236 contract, and `render-skills.py --check`.
- `.cache/final-validation.md` in this run folder, `verdict: pass`, bound to worktree hash `2d1d90d773360a60a4eaa549253081fd60477ed4f7ead4aba22a1f8c22948d91`.
- Mission ledger: `kaola-workflow/.ledger/issue-236.jsonl` (one done mission).

## Known failures or unverified scope

- `./scripts/render-skills.py --check` and `--write` exit 1 before comparing or writing generated files. The check listed 10 pin findings: 4 pre-existing `kaola-workflow/archive/issue-235/*` paths and 6 paths from this change. Pin-engine repair was owner-excluded. Generated `hosts/grok-bot/INSTALL.md` was byte-checked against the renderer by `test-issue-236-install-completion.py`.
- No live CLI upgrade, no live ACP session, no release, no tag, and no CHANGELOG release section.
- `kaola-workflow-run-chains.js --project issue-236` returned `chains_config_missing` (no `test:kaola-workflow:*` scripts). The consumer gate is the recorded final-validation file.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- README.md
- docs/api.md
- docs/grok-bot-host.md
- hosts/grok-bot/INSTALL.md
- scripts/install-local.sh
- templates/grok-bot/INSTALL.md.tmpl
- tests/contract/test-installer-runtimes.sh
- tests/contract/test-issue-236-install-completion.py

## Follow-Up Items

None. The pin-allowlist failure is the pre-existing main condition the owner excluded from this issue; no follow-up was filed.

## Final readiness

Host acceptance passed. Ready to archive and merge-sink `workflow/issue-236`, then close issue #236.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-236/.cache/final-validation.md
- kaola-workflow/archive/issue-236/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-236/finalization-summary.md
- kaola-workflow/archive/issue-236/mission-ledger.jsonl
- kaola-workflow/archive/issue-236/workflow-state.md
