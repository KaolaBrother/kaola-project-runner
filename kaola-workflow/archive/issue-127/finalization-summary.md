# Finalization Summary — issue-127

## Delivered
Grok 4.6→4.7 adaptation for the `grok` and `cursor-cli` workers, using live-measured names (Host ruling Option 1). The Cursor 4.7 picker ids dropped the `cursor-` prefix:
- cursor-cli default `grok-4.7-xhigh`; `acp_model_map` `grok-4.7-xhigh[-fast]=grok-4.7`.
- TUI footer `Grok 4.7 256K Extra High`, parsed to `grok-4.7-{effort}[-fast]`. This covers the scrolled-header fallback at kaola-model-policy.py:353, which the issue's case-sensitive grep missed.
- grok default/upgrade `grok-4.7`.
- Cursor `acp_verified_versions` `cli=2026.09.15-d2fe57e`.
- Errata comment on #127: issuecomment-5765065615.
Candidate: af6b45d (base main 253bbe8).

## Files Changed
17 source files: 51 literal replacements, plus the policy regex, return value and fallback, plus the new test. 28 generated files under skills/, produced by render --write. The full list is under Changed Paths.

## Test Coverage
- New: `test_cursor_grok_47_footer_is_parsed` in tests/contract/test-model-policy.sh. It feeds the measured footer plus the 4.6 banner tip line and expects `grok-4.7-xhigh-fast`, `{xhigh, fast:true}`, verified, source `cursor-main-tui`. GREEN.
- Updated assertions: test-acp-contract, test-generated-skills, test-issue-98-dsh-acp, test-lifecycle-contract:98, the mock and fake ACP agents, and the synthetic raw-mode-tui fixture.
- ready-cursor-x0.frame.txt (a real capture from 2026.08.25) is kept unchanged as dated evidence.

## Validation
- `./scripts/render-skills.py --check && ./scripts/validate.sh`: render PASS; validate rc=0, 0 RED (log: validate.log). Run on a tree byte-identical to af6b45d. `.cache/final-validation.md` verdict pass, validated_candidate_hash 9a211562e4fb….
- run-chains: chains_config_missing (consumer repo; gated on final-validation.md).
- Outside the gate: test-model-policy.sh has 12 RED and test-lifecycle-contract.py has 9 RED. Both sets are identical at base 253bbe8 (diffed), so they are pre-existing and filed as #128. test-observation-contract.py: OK.
- Acceptance legs:
  - Live, read-only: `agent --list-models`; ACP initialize+session/new on both CLIs; Cursor TUI footer via `CURSOR_CONFIG_DIR=<tmp> cursor-agent --trust --model …`. The real ~/.cursor/cli-config.json mtime and size were unchanged. Record: live-confirm.md.
  - Host acceptance: PASS, 2026-09-22.

## Issue walk (#127 acceptance)
1. render --write/--check PASS; validate.sh rc=0.
2. Section D assertions synced. A case-insensitive `4\.6` grep leaves only the dated items kept on purpose: test-lifecycle-contract.py:108 and ready-cursor-x0.frame.txt.
3. skills/ changed only through render (--check PASS).
4. No unrelated refactor: grok-golden, alt/upgrade semantics and dated history are untouched. The Cursor name and regex shape changes are a Host-ruled factual correction to measured values.
5. CHANGELOG Unreleased entry added.

## Changed Paths
- AGENTS.md
- CHANGELOG.md
- docs/conventions.md
- platforms/cursor-cli.yaml
- platforms/grok.yaml
- scripts/adapters/cursor-cli.sh
- scripts/adapters/grok.sh
- scripts/kaola-acp.py
- scripts/kaola-model-policy.py
- tests/contract/fake-droid-acp-agent.py
- tests/contract/mock-acp-agent.py
- tests/contract/test-acp-contract.py
- tests/contract/test-generated-skills.py
- tests/contract/test-issue-98-dsh-acp.py
- tests/contract/test-lifecycle-contract.py
- tests/contract/test-model-policy.sh
- tests/fixtures/observations/claude-code/raw-mode-tui.py
- skills/** (28 generated files via render-skills.py --write)

## Documentation Docking
DOCKED — see .cache/doc-docking.md (AGENTS.md, docs/conventions.md, CHANGELOG.md fixed; README, api, architecture no impact; dated docs kept).

## Follow-Up Items
- filed: #128 (P3). The contract suites test-model-policy.sh and test-lifecycle-contract.py are red on main and are not named in validate.sh. Verified OPEN, body 2318 chars.
- Not filed (not a defect): Cursor steering_summary cites cli 2026.09.10-fd3934a; it was not re-measured this run.

## Readiness
READY — Host accepted; closure decision: close #127.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-127/.cache/doc-docking.md
- kaola-workflow/archive/issue-127/.cache/final-validation.md
- kaola-workflow/archive/issue-127/.cache/mirror-digest.json
- kaola-workflow/archive/issue-127/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-127/errata-comment.md
- kaola-workflow/archive/issue-127/finalization-summary.md
- kaola-workflow/archive/issue-127/live-confirm.md
- kaola-workflow/archive/issue-127/mission-list.md
- kaola-workflow/archive/issue-127/workflow-state.md
