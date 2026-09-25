# Finalization Summary — issue #168

## Delivered

The three incomplete `reported_drift` enumerations now name all five values:
`pin-drift`, `cli-drift`, `quota-drift`, `recorded-path-missing` (a recorded
script path no longer exists), and `install-root-mismatch` (the seat's
install tree moved or was re-rooted).

- Seat-stale refusal detail in `scripts/kaola-acp.py`, prose, plus its ten
  rendered copies.
- Worker status paragraph in `templates/references/acp.md.tmpl` and rendered
  `references/acp.md`.
- ZCode Host dispatch paragraph in
  `templates/orchestrator/references/zcode-host-dispatch.md.tmpl` and the
  rendered reference, keeping the #166 file-per-value style for the first
  three values.

Seat behavior is unchanged. No tag, release, or pin.

Implementation commit: `45706ef26a7d958880229c20560b33f84f9edb10`.

Claude Code review verdict, accepted before this finalize: `VERDICT: PASS
for issue #168`. Receipt: `/tmp/kpr-i168-review-receipt.json`. The reviewer's
`test-issue-98-dsh-acp.py` flake also fails on base and is not this change.

## Files Changed

`scripts/kaola-acp.py`, both templates, ten rendered worker copies of
`kaola-acp.py` and `references/acp.md`, ten `main-skill-build.json` stamps,
`skills/kaola-project-runner/references/zcode-host-dispatch.md`,
`scripts/validate.sh`, `tests/contract/test-issue-168-drift-enumeration.py`,
and `CHANGELOG.md`.

## Test Coverage

- `./scripts/validate.sh` — exit 0 on `45706ef`. Log:
  `/tmp/kpr-i168-validate.log` (`EXIT:0`). Includes
  `test-issue-168-drift-enumeration.py` (1 test, OK).
- `./scripts/render-skills.py --check` — PASS inside that same log.
- Named skips: bash 3.2.57 lacks `mapfile`/`BASHPID`, so the #151 watchdog
  wrapper is skipped and those suites run unwatched. No other skips.
- Live per-platform ACP smoke was not run. Acceptance was the offline
  contract gate plus the independent Claude Code review PASS.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- scripts/kaola-acp.py
- scripts/validate.sh
- skills/claude-code-kaola-project-runner/references/acp.md
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/references/acp.md
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/references/acp.md
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/references/acp.md
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/references/acp.md
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/references/acp.md
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/references/acp.md
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/zcode-host-dispatch.md
- skills/kimi-cli-kaola-project-runner/references/acp.md
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/references/acp.md
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/references/acp.md
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/references/zcode-host-dispatch.md.tmpl
- templates/references/acp.md.tmpl
- tests/contract/test-issue-168-drift-enumeration.py

## Documentation Docking

DOCKED — see `.cache/doc-docking.md`.

## Follow-Up Items

None. The review recorded no blocking findings. The `test-issue-98-dsh-acp.py`
flake is pre-existing on base and was not introduced here.

## Final Readiness Status

READY — validation is recorded against `45706ef`, documentation is docked,
and the merge sink is authorized. No tag, release, or pin.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-168/.cache/doc-docking.md
- kaola-workflow/archive/issue-168/.cache/final-validation.md
- kaola-workflow/archive/issue-168/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-168/finalization-summary.md
- kaola-workflow/archive/issue-168/mission-ledger.jsonl
- kaola-workflow/archive/issue-168/workflow-state.md
