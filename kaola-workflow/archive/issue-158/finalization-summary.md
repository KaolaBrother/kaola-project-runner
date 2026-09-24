# Finalization summary — issue-158

## Delivered
Issue #158: the invalid-dsh-mode refusal in `scripts/kaola-acp.py` named the internal `--mode` flag; it now names the Agent-facing wrapper flag `--permission-mode` (`kaola-tmux.sh` accepts `--permission-mode` and forwards it as `--mode`). Accepted value set unchanged (read-only, workspace-write, danger-full-access, or bypassPermissions); internal flag and wrapper forwarding untouched. Sweep of `scripts/kaola-acp.py`: no other Agent-facing text names `--mode` (line 77 is an internal code comment; `--mode` has no argparse help).
- e6e4cc9 fix(acp): #158 dsh mode refusal names --permission-mode

## Files Changed
scripts/kaola-acp.py, tests/contract/test-issue-98-dsh-acp.py, and the 10 renderer-vendored copies skills/*/scripts/kaola-acp.py (byte-identical to source after `render-skills.py --write`, Host ruling A).

## Test Coverage
`tests/contract/test-issue-98-dsh-acp.py::Issue120DshPermissionModeThroughTheRunner::test_an_unknown_mode_is_refused_before_spawn` pins the full new refusal wording (value set included) and asserts the old `--mode for dsh` text is absent; updated in the same commit as the text it pins. File: 37/37 OK.

## Validation
- `./scripts/render-skills.py --check` rc=0 and `./scripts/validate.sh` rc=0 on e6e4cc9, Mac Studio, bash 3.2 (watchdog rows run unwatched with a named SKIP receipt, #151). Recorder: `.cache/final-validation.md` verdict pass.
- Pre-ruling measurement: with only the source edit, `render --check` rc=1 (10 stale vendored copies) — the reason for Host ruling A.
- Host acceptance: GRANTED (commit shape, scope fence, both rc values, ledger 2/2 independently verified).
- Unexecuted: no live dsh ACP run (the refusal fires before spawn; the contract test exercises the exact code path).

## Changed Paths
- scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- tests/contract/test-issue-98-dsh-acp.py

## Documentation Docking
DOCKED — see `.cache/doc-docking.md` (no doc quotes the refusal wording; docs/api.md already names `--permission-mode`).

## Follow-Up Items
- None filed. Run observation (environment, not a repo defect): git identity is not configured on this machine and the hostname now resolves to `bogon`, so author auto-detection fails; e6e4cc9 used the prior commits' identity via one-shot `git -c` (no config written).

## Issue Statement Walk
- Measured (refusal names `--mode`): fixed at scripts/kaola-acp.py:3375.
- Remedy (name `--permission-mode`, value set unchanged, pin with a contract test): refusal text + pin test above.

## Readiness
READY — closure decision: close #158.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-158/.cache/doc-docking.md
- kaola-workflow/archive/issue-158/.cache/final-validation.md
- kaola-workflow/archive/issue-158/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-158/finalization-summary.md
- kaola-workflow/archive/issue-158/mission-ledger.jsonl
- kaola-workflow/archive/issue-158/workflow-state.md
