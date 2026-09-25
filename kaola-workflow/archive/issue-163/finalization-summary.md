# Finalization Summary — issue #163

## Delivered

`drain-restart` now carries the platform default permission mode when no mode
was recorded or passed. Explicit and recorded modes retain precedence. The
selection-unknown refusal now accounts for the complete start selection,
including `mode`.

The candidate was rebased from `a054fb6` onto current main
`d283283c10c3f96f2e58406214651498403997ef`. The rebase had one
`CHANGELOG.md` content conflict; it was resolved by retaining both the landed
Issue #164 entry and the Issue #163 entry.

## Files Changed

The product changes are in `scripts/kaola-acp.py`, `scripts/kaola-tmux.sh`,
their generated worker copies, `tests/contract/test-issue-162-upgrade-safety.py`,
`CHANGELOG.md`, and `docs/api.md`. Generated copies were validated from the
shared source; no generated surface was hand-edited.

## Test Coverage

- `./scripts/validate.sh` — exit 0, 889 tests across 45 unittest suites.
- Validation log: `/tmp/kpr-i163-finalize-validate.log`.
- The full live per-platform ACP smoke was not run; Host acceptance and the
  offline contract validation are the acceptance evidence for this run.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- scripts/kaola-acp.py
- scripts/kaola-tmux.sh
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-tmux.sh
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-tmux.sh
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-tmux.sh
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-tmux.sh
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-tmux.sh
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-tmux.sh
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-tmux.sh
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-tmux.sh
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-tmux.sh
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-tmux.sh
- tests/contract/test-issue-162-upgrade-safety.py

## Documentation Docking

DOCKED — see `.cache/doc-docking.md`. `CHANGELOG.md` and `docs/api.md` cover
the changed behavior; README and architecture/conventions documentation were
checked and did not require changes.

## Follow-Up Items

None. Issue #163 closure is skipped; the Host closes it after the verified
sink. No GitHub issue actions were performed.

## Final Readiness Status

READY — candidate frozen at `b73626bebf553ca154f5ad2c0ecec18e39114333`.
No tag, release, or pin commit.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-163/.cache/doc-docking.md
- kaola-workflow/archive/issue-163/.cache/final-validation.md
- kaola-workflow/archive/issue-163/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-163/finalization-summary.md
- kaola-workflow/archive/issue-163/mission-ledger.jsonl
- kaola-workflow/archive/issue-163/workflow-state.md
