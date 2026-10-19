# Finalization Summary — issue-360

## Delivered

`platforms/dsh.yaml` `acp_env_allowlist` now names `DSH_BIN` and
`DSH_PERMISSION_MODE`, the two Runner-injected launch variables the launchd
broker's `filter_env` was dropping (matching the codex `CODEX_PATH` /
claude `CLAUDE_BIN` convention). A broker-launched dsh holder ran under dsh's
own `workspace-write` default while `start` reported `danger-full-access`
applied. The broker `submit` ready receipt now carries `env_keys`, the sorted
names of the delivered environment (never values; a reconciled `existing`
answer carries no census because that submit spawned nothing).
`config_application.mode` reports `applied` from the delivered environment:
a direct spawn reads back `holder_env`, a brokered fresh spawn checks the
census (`dropped-by-launch-env-filter` when absent), an `existing` reconcile
reports `applied: false` with `existing-holder-env-not-redelivered`, and a
ready answer missing the census reports `env-census-absent`. Merged with
#363 on rebase: a `start --resume`/`--continue` keeps its
`resumed-session-permission` receipt shape unchanged.

## Candidate

Branch `workflow/issue-360`, one commit `b463335f` rebased onto main tip
`153409b8` (includes #365, #367, #363). Rebase conflict resolution:
`CHANGELOG.md` keeps all five Unreleased bullets; `scripts/kaola-acp.py`
merges both mode semantics (resume → #363's `resumed-session-permission` +
`effective` session-log readback; fresh start → the delivered-env census);
`platforms/dsh.yaml` auto-merged (allowlist + permission_summary both kept);
all 13 generated `skills/*/scripts/kaola-acp.py` re-rendered.

## Evidence

- Reproduction on the pre-fix tree: `filter_env` with the old allowlist
  returned `['DSH_HOME', 'HOME', 'PATH']` — `DSH_PERMISSION_MODE` dropped,
  matching the issue's minimal repro.
- `./scripts/render-skills.py --check` → PASS (content stage, budgets OK).
- `./scripts/validate.sh --suite test-issue-98-dsh-acp.py --suite
  test-issue-266-launch-broker.py --suite
  test-issue-266-launch-broker-composed.py --suite
  test-issue-363-dsh-resume-permission.py` on candidate `b463335f`:
  test-issue-98-dsh-acp 46/46 OK (13.5s, includes the new broker-path tests
  and the unchanged #120 direct-spawn tests); test-issue-363 10/10 OK;
  test-issue-266-launch-broker PASS; test-issue-266-launch-broker-composed
  PASS (48 checks, 0 failures); cleanup reported no residual pids.
- Recorded receipt: `kaola-workflow/issue-360/.cache/final-validation.md`
  (verdict pass, bound to this tree).
- Host acceptance: user re-ran test-issue-98 (46/46 OK) and both broker
  suites green in a clean environment, then approved content and released
  finalization.

## Known failures or unverified scope

- The 134-suite full inventory was not run on this candidate; per AGENTS.md
  the focused suites plus render check were the agreed scope, and the Host
  runs the full inventory at its own boundary.
- Resumed dsh sessions keep the permission recorded in the session log; the
  receipt for that path is #363's `resumed-session-permission` shape, which
  this merge preserves. Live smoke on a real dsh seat was out of scope per
  the run constraint (new session only, no resume).
- `env_keys` is additive inside schema `kaola-launch-broker/3` — broker and
  client ship in the same Skill directory, so no cross-version pairing
  exists.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- platforms/dsh.yaml
- scripts/kaola-acp.py
- scripts/kaola-launchd-broker.py
- skills/antigravity-kaola-project-runner/scripts/kaola-acp.py
- skills/antigravity-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/dsh-kaola-project-runner/scripts/platform.yaml
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-launchd-broker.py
- tests/contract/test-issue-266-launch-broker.py
- tests/contract/test-issue-98-dsh-acp.py

## Follow-Up Items

None filed: no new run-discovered defect surfaced. The resumed-session
permission behavior observed while fixing this issue was already tracked
as #363 and landed on main (`0d14f016`) during this run; the rebase merged
both semantics and `test-issue-363-dsh-resume-permission.py` stays green.

## Final readiness

Ready to sink: content accepted by the Host, validation green on the
rebased candidate, CHANGELOG Unreleased entry present (`Seats: restart
required` — `platforms/` is in the operator restart set).

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-360/.cache/final-validation.md
- kaola-workflow/archive/issue-360/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-360/finalization-summary.md
- kaola-workflow/archive/issue-360/mission-ledger.jsonl
- kaola-workflow/archive/issue-360/workflow-state.md
