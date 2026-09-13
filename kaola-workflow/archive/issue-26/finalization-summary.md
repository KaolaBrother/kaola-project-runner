# Finalization Summary

## Delivered

Issue #26: host-wide `kaola-acp list` emits `kaola-acp-list/1` for live holders; `kaola-acp <platform> view` emits typed `kaola-acp-view/1` (plan full-replace, per-`toolCallId` cards, view options `{optionId,name,kind}`). EventLog restores max cursor from live plus rotated `.jsonl.1–.3`. `install-local.sh` installs owned `$HOME/.local/bin/kaola-acp` and `kaola-acp-holder` symlinks. L0 `send --wait` keys are unchanged. Socket-close on `view` remaps to `holder-unreachable`/`holder-lost`; `kaola-tmux.sh … view` returns `view-unsupported`. Golden Grok bytes unchanged. Follow (#27) and permit lock (#25) were not implemented.

## Files Changed

`scripts/kaola-acp.py`, `scripts/kaola-acp-holder.py`, `scripts/install-local.sh`, `scripts/kaola-tmux.sh`, `scripts/validate.sh`, `templates/references/acp.md.tmpl`, generated Skills, `tests/contract/test-acp-watch-contract.py`, `tests/contract/fixtures/kaola-acp-view-1.sample.json`, `tests/contract/mock-acp-agent.py`, README, CHANGELOG, and ACP Watch / API / architecture docs.

## Test Coverage

- `tests/contract/test-acp-watch-contract.py` 10 OK (was RED 7 FAIL / 1 PASS on unimplemented `list`/`view`/bin-install).
- `tests/contract/test-acp-contract.py` 14 OK.
- `./scripts/render-skills.py --check` PASS (6 Skills).
- `./scripts/validate.sh` PASS at `c123d47`.
- Live CLI UAT against a real platform binary was not executed.

## Validation

`./scripts/validate.sh` — PASS, candidate hash `e98b0b65025c8969255b0531bcc26c3afaec01ec7dd385cbcdaa618b61a12be6` at `c123d47`.

`git diff --stat templates/grok-golden` — empty.

## Changed Paths

finalize `--check` `changed_paths`:
`scripts/install-local.sh`, `scripts/kaola-acp-holder.py`, `scripts/kaola-acp.py`, `scripts/kaola-tmux.sh`, `scripts/validate.sh`, `skills/claude-code-kaola-project-runner/references/acp.md`, `skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py`, `skills/claude-code-kaola-project-runner/scripts/kaola-acp.py`, `skills/claude-code-kaola-project-runner/scripts/kaola-tmux.sh`, `skills/cursor-cli-kaola-project-runner/references/acp.md`, `skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py`, `skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py`, `skills/cursor-cli-kaola-project-runner/scripts/kaola-tmux.sh`, `skills/devin-kaola-project-runner/references/acp.md`, `skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py`, `skills/devin-kaola-project-runner/scripts/kaola-acp.py`, `skills/devin-kaola-project-runner/scripts/kaola-tmux.sh`, `skills/grok-kaola-project-runner/references/acp.md`, `skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py`, `skills/grok-kaola-project-runner/scripts/kaola-acp.py`, `skills/grok-kaola-project-runner/scripts/kaola-tmux.sh`, `skills/kimi-cli-kaola-project-runner/references/acp.md`, `skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py`, `skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py`, `skills/kimi-cli-kaola-project-runner/scripts/kaola-tmux.sh`, `skills/opencode-kaola-project-runner/references/acp.md`, `skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py`, `skills/opencode-kaola-project-runner/scripts/kaola-acp.py`, `skills/opencode-kaola-project-runner/scripts/kaola-tmux.sh`, `templates/references/acp.md.tmpl`, `tests/contract/fixtures/kaola-acp-view-1.sample.json`, `tests/contract/mock-acp-agent.py`, `tests/contract/test-acp-watch-contract.py`.

`git diff --name-only origin/main...HEAD` also includes `CHANGELOG.md`, `README.md`, `docs/README.md`, `docs/acp-watch/README.md`, `docs/acp-watch/list-view.md`, `docs/api.md`, `docs/architecture.md`, and `docs/runner-v2-dual-transport-design.md` (present on the branch, omitted from that check list).

## Documentation Docking

DOCKED in `.cache/doc-docking.md`.

## Follow-Up Items

None. Issues #25 (permit lock) and #27 (follow) remain the open Watch successors; they were out of scope.

## Readiness

READY for all-or-nothing closure and merge sink of issue #26.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-26/.cache/doc-docking.md
- kaola-workflow/archive/issue-26/.cache/final-validation.md
- kaola-workflow/archive/issue-26/.cache/implement-verify.md
- kaola-workflow/archive/issue-26/.cache/mirror-digest.json
- kaola-workflow/archive/issue-26/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-26/.cache/repair-verify.md
- kaola-workflow/archive/issue-26/.cache/review-correctness.md
- kaola-workflow/archive/issue-26/.cache/review-test-custody.md
- kaola-workflow/archive/issue-26/.cache/review-trust-boundary.md
- kaola-workflow/archive/issue-26/.cache/tdd-red-proof.md
- kaola-workflow/archive/issue-26/finalization-summary.md
- kaola-workflow/archive/issue-26/mission-list.md
- kaola-workflow/archive/issue-26/workflow-state.md
