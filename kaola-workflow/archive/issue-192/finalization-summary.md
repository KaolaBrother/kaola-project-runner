# Finalization Summary — issue-192

## Delivered

Issue #192 now declares verified quota reset windows for the current package IDs, distinguishes Kimi's weekly-plus-monthly and monthly-only variants, updates the Project Runner quota reference examples, and documents why known periods are not treated as absent when a provider leaves another pool's periods unspecified. Host accepted candidate `7e73818df90bcdfe2dc51a86048df1e943e29b22` after the rejected `8a7da798` candidate's two reported gaps were repaired. The candidate contains the non-rewriting sync merge `82ba8e3f` from the then-current main after #194's sink at `ad73e158`.

Factory's Individual Plans documentation establishes Standard Usage's independent 5-hour, 7-day, and 30-day rolling windows. `droid:standard` lists `5h`, `weekly`, and `monthly`. Core has separate Rate Limits, but Factory does not specify Core-specific periods; the catalog retains only the owner-confirmed weekly and monthly periods and does not infer 5h. Extra Usage is prepaid and non-expiring. The `kaola-acp-packages/1` schema remains unchanged.

## Files Changed

The accepted branch changes 46 paths from its merge base: quota catalog implementation and all ten platform package manifests; regenerated worker quota scripts and manifest payloads; `docs/api.md`; the orchestrator quota reference and its rendered copy; generated build metadata; and `tests/contract/test-issue-148-quota-packages.py`. The final repair also verifies that the Grok and Droid reference examples parse to the exact package CLI output.

## Test Coverage

- `python3 tests/contract/test-issue-148-quota-packages.py`: 16 tests passed.
- `./scripts/render-skills.py --write`: passed; `./scripts/render-skills.py --check`: passed, budgets OK.
- `./scripts/validate.sh`: `EXIT_CODE=0`; full log at `/tmp/kpr-i192-validate-20260927.log`. macOS Bash 3.2 produced the documented watchdog-skip receipts for affected lanes while the suites ran.
- `kaola-acp packages --platform grok` returned `grok:account` with `windows: ["weekly"]`; `kaola-acp packages --platform droid` returned Standard `["5h", "weekly", "monthly"]`, Core `["weekly", "monthly"]`, and Extra Usage `[]` under schema `/1`.
- Live Droid ACP smoke on `droid-KPR-i192-quota-recheck` returned exactly `KPR_I192_LIVE_OK`, with zero tool calls and zero file changes; exact-session stop succeeded and final status was stopped.
- Host acceptance reviewed exact candidate `7e73818df90bcdfe2dc51a86048df1e943e29b22`. Factory plan facts were checked against [Individual Plans](https://docs.factory.ai/pricing/individuals).
- The prior broad ACP smoke on the earlier candidate left OpenCode inconclusive. Host accepted the focused and full validation receipts and directed that no broader repeat was needed for this repair.
- No consumer UAT, install, or release was performed.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- docs/api.md
- platforms/claude-code.yaml
- platforms/codex.yaml
- platforms/cursor-cli.yaml
- platforms/devin.yaml
- platforms/droid.yaml
- platforms/dsh.yaml
- platforms/grok.yaml
- platforms/kimi-cli.yaml
- platforms/opencode.yaml
- platforms/zcode.yaml
- scripts/kaola-quota.py
- skills/claude-code-kaola-project-runner/scripts/kaola-quota.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/platform.yaml
- skills/codex-kaola-project-runner/scripts/kaola-quota.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/platform.yaml
- skills/cursor-cli-kaola-project-runner/scripts/kaola-quota.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/platform.yaml
- skills/devin-kaola-project-runner/scripts/kaola-quota.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/platform.yaml
- skills/droid-kaola-project-runner/scripts/kaola-quota.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/platform.yaml
- skills/dsh-kaola-project-runner/scripts/kaola-quota.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/platform.yaml
- skills/grok-kaola-project-runner/scripts/kaola-quota.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/platform.yaml
- skills/kaola-project-runner/references/quota-packages.md
- skills/kimi-cli-kaola-project-runner/scripts/kaola-quota.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/kimi-cli-kaola-project-runner/scripts/platform.yaml
- skills/opencode-kaola-project-runner/scripts/kaola-quota.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/platform.yaml
- skills/zcode-kaola-project-runner/scripts/kaola-quota.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/platform.yaml
- templates/grok-bot/accepted-revision.json
- templates/orchestrator/references/quota-packages.md
- tests/contract/test-issue-148-quota-packages.py

## Documentation Docking

DOCKED — see `.cache/doc-docking.md`. The API and consumer reference document the actual windows shape, display rule, confirmed versus unknown periods, and the Factory Standard/Core distinction. README, CHANGELOG, architecture, conventions, and AGENTS.md require no update for this package metadata change; no setup, command, release, or top-level architecture behavior changed.

## Follow-Up Items

None filed. `claude-code:extra_usage`, `devin:overage`, and `opencode:zen` remain null with package-specific reasons in the API/reference documentation. The unknown Core-specific periods are not guessed. #193's docs/api.md installer hunk is separate from this issue's quota hunk. The accepted sink order is #192 first; the Host directed #193 and #195 owners to sync only after this sink. #195 must rerender and revalidate the shared generated `main-skill-build.json` files before its own acceptance/merge. This run does not edit either sibling branch or worktree.

## Status

READY — merge sink, verified issue closure, archive.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-192/.cache/doc-docking.md
- kaola-workflow/archive/issue-192/.cache/final-validation.md
- kaola-workflow/archive/issue-192/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-192/finalization-summary.md
- kaola-workflow/archive/issue-192/mission-ledger.jsonl
- kaola-workflow/archive/issue-192/workflow-state.md
