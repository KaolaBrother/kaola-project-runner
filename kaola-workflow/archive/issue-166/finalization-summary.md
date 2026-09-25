# Finalization Summary — issue #166 bundle

## Delivered

Issue #166 now reports `quota-drift` in `status` and `list` when a recorded
`kaola-quota.py` digest changes, without changing the documented stale-seat
contract. Legacy records without a quota digest remain silent. Issue #167's
pin-drift contract test name now states that pin drift is reported but not
stale without a Skill difference.

Implementation commit after update onto current main:
`27f85ed37bc76da2f70ac542430a8b6caec1c678`.

Host acceptance is complete and the claude-code pre-sink review returned PASS
for both #166 and #167 on the frozen delivery before this finalize update.
The current candidate is the rebased equivalent on main `0407928`.

This run does not tag, release, or write a pin.

Issue members:

1. **#166** — quota-only drift is named in `reported_drift`, remains
   non-stale, and is covered in `status` and `list`; legacy records are
   covered separately.
2. **#167** — the pin-drift test is renamed to match its
   reported-not-stale assertion.

Issue closure is intentionally skipped. The Host closes #166 and #167
separately after the sink with their own evidence.

## Files Changed

The delivery commit changes 36 product/generated/template/test files relative
to current main. `scripts/validate.sh` is unchanged; the existing #162
contract file already runs the bundled coverage. The #163 drain-restart tests
and #164 validation lane remain in the updated branch.

## Test Coverage

- `./scripts/validate.sh` — exit 0 on the updated candidate, including the
  20-test `test-issue-162-upgrade-safety.py` suite and the 5-test Issue #164
  lane. Log: `/tmp/kpr-i166-finalize-validate.log`.
- The first full run encountered one transient
  `acp-initialize-timeout` in Issue #98; the isolated lane passed 37/37, and
  the complete rerun passed. Isolated retry log:
  `/tmp/kpr-i166-dsh-retry.log`.
- Environment skips are recorded in the validation log: Bash 3.2.57 lacks
  `mapfile`/`BASHPID`, so watchdog execution is skipped; two Issue #101
  watchdog tests are skipped for the same named prerequisite.
- Live per-platform ACP smoke was not run. Host acceptance was the offline
  contract gate.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- scripts/kaola-acp.py
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
- tests/contract/test-issue-162-upgrade-safety.py

## Documentation Docking

DOCKED — see `.cache/doc-docking.md`.

## Follow-Up Items

None. No run-discovered defect.

## Final Readiness Status

READY — validation is recorded against the rebased candidate, documentation
is docked, and the merge sink is authorized. No tag, release, or pin.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-166/.cache/doc-docking.md
- kaola-workflow/archive/issue-166/.cache/final-validation.md
- kaola-workflow/archive/issue-166/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-166/finalization-summary.md
- kaola-workflow/archive/issue-166/mission-ledger.jsonl
- kaola-workflow/archive/issue-166/workflow-state.md
