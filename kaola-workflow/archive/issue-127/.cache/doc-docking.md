# Documentation docking — issue-127 (candidate af6b45d)

Checked against AGENTS.md documentation map and the #127 inventory.

| file | outcome |
|---|---|
| AGENTS.md | fixed: line 99 live Cursor slug `grok-4.7-xhigh` (pinned by tests/contract/test-lifecycle-contract.py:98, updated in step) |
| docs/conventions.md | fixed: lines 145-146 slug `grok-4.7-xhigh`, footer `Grok 4.7 256K Extra High` |
| CHANGELOG.md | fixed: Unreleased entry for Issue #127 |
| README.md | no impact: no Grok 4.6 / cursor-grok literal |
| docs/api.md | no impact: no model literal |
| docs/architecture.md | no impact: no model literal, no architectural change |
| docs/live-smoke-*, docs/decisions/*, docs/poc-*, docs/runner-v2-*, docs/acp-live-verification-2026-09-11.md | intentionally unchanged: dated historical measurements (#127 section G) |
| skills/, hosts/grok-bot/ | generated via render-skills.py --write; --check PASS |
| platforms/cursor-cli.yaml steering_summary | intentionally unchanged: steering fact measured on cli 2026.09.10-fd3934a, not re-measured this run |

DOCKED
