# Finalization Summary — issue #164

## Delivered

`preflight`, `start`, and `drain-restart` share one bridge-file and ZCode-runtime presence decision (`bridge_runtime_error`). Pre-spawn `acp-bridge-missing` and `acp-runtime-missing` receipts carry the same `bridge` / `runtime_binary` facts preflight reports (`bridge_facts` with version), and still leave `mutation_status` `not_started` and `mutation_performed` false. A drain-restart refusal still carries `action` and `start_selection`.

Implementation commit (frozen, Host-accepted): `89fc21bd780216e8e7a850729c7472c95fb5a547`.

This run does not tag, release, or write a pin.

Issue members:

1. One shared presence decision — `scripts/kaola-acp.py` `bridge_runtime_error`, called from `command_preflight` and `pre_spawn_refusal`. The copy in `command_start` is gone.
2. Pre-spawn refusals carry preflight's bridge facts — `pre_spawn_refusal` calls `bridge_facts(args, with_version=True)` before returning `acp-bridge-missing` or `acp-runtime-missing`.
3. Contract coverage — `tests/contract/test-issue-164-pre-spawn-bridge-facts.py` (start and drain-restart, missing bridge and missing ZCode runtime).

## Files Changed

Product commit `89fc21b` (14 files). Sources: `scripts/kaola-acp.py`, `scripts/validate.sh`, `tests/contract/test-issue-164-pre-spawn-bridge-facts.py`, `CHANGELOG.md`. Generated worker `skills/*/scripts/kaola-acp.py` copies come from `./scripts/render-skills.py --write` and match the source script.

## Test Coverage

- `python3 tests/contract/test-issue-164-pre-spawn-bridge-facts.py -v` — 5/5 OK (Host acceptance and this finalize run).
- `./scripts/render-skills.py --check` — PASS.
- `./scripts/validate.sh` — EXIT 0 on the frozen candidate before Host acceptance (`/tmp/kpr-issue-164-validate.log`) and again for this finalize record.
- Live per-platform ACP smoke was not run. Host acceptance is the offline contract gate.

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
- tests/contract/test-issue-164-pre-spawn-bridge-facts.py

## Documentation Docking

DOCKED — see `.cache/doc-docking.md`. `CHANGELOG.md` Unreleased already states the refusal fact set. `docs/api.md` already reports `bridge` on preflight and start and names `acp-bridge-missing`. No documentation file was edited during finalization.

## Follow-Up Items

None. No run-discovered defect. Issue #164 stays open: the Host defers closure until an independent claude-code review PASSes on final main. This finalize does not close, comment on, or edit the issue.

## Final Readiness Status

READY — candidate frozen at `89fc21bd780216e8e7a850729c7472c95fb5a547`, Host acceptance granted. Archive and merge-sink are the next transaction. No tag, no release, no pin. Issue closure is skipped.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-164/.cache/doc-docking.md
- kaola-workflow/archive/issue-164/.cache/final-validation.md
- kaola-workflow/archive/issue-164/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-164/finalization-summary.md
- kaola-workflow/archive/issue-164/mission-ledger.jsonl
- kaola-workflow/archive/issue-164/workflow-state.md
