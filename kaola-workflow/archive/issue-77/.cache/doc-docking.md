# Documentation docking - Issue #77

Status: DOCKED

## Scope of the change

Test-only: `tests/contract/test-issue-73-canonical-root.py`, +12/-0 lines, confined to
`TestPreservedBehavior::test_standalone_acp_start_in_a_child_worktree_is_not_refused`.
No production module, no script, no generated surface, no public behavior changed.

## Checklist walked against AGENTS.md

| Surface | Verdict |
|---|---|
| APIs / signatures | no impact - no production code touched |
| Setup / install (`install-local.sh`, `render-skills.py`) | no impact - generated output unchanged; `render-skills.py --check` PASS |
| Architecture (`docs/`) | no impact - the canonical-root guard and holder lifecycle are unchanged; only a test now reaps what it created |
| Environment / prerequisites | no impact - no new tool, binary, or env var |
| Validation policy (`AGENTS.md`, `scripts/validate.sh`) | no impact - same two commands, same suite list; the suite was already registered in `validate.sh` (lane B) |
| README | no impact - user-facing usage unchanged |
| API docs | no impact |
| Changelog (`CHANGELOG.md`) | deliberately not updated - CHANGELOG records user-visible changes, and a contract-test cleanup is not user-visible |
| Examples | no impact |

## Facts transcribed from the real artifacts

- `/bin/false` absent on macOS: `ls /bin/false` -> `No such file or directory`; `/usr/bin/false` exists.
- Holder state on this fixture's spawn failure: `{"error":{"code":"acp-spawn-failed"},"state":"error"}`.
- `render-skills.py --check` -> `render-skills: PASS (9 workers + kaola-project-runner + grok-bot host: 1 bridge skill, 2526 B, content stage, unpinned (not saveable); budgets OK)`.
- `./scripts/validate.sh` -> exit 0.

The in-code comment added by this change is the documentation that matters here: it is docked to the
verified mechanism (state `error`, spawn failure) rather than the issue's original wording.
