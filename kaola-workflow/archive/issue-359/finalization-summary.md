# Finalization Summary — issue-359

## Delivered

A durable host registry closes the record-dir-loss blind spot in dead-holder
wakes. `start` for `session_role` `host` registers a row in
`<repo>/.kaola/host-registry.json` (`kaola-host-registry/1`, mode 0600, atomic
replace under `host-registry.lock`; `SWEEP_KAOLA_OWN` covers both names) and a
recorded clean `stop` removes it — the holder deregisters itself on a
socket-answered stop or idle exit, and the CLI stop path covers dead-record
sweeps and older holders. The `delegator-webhook status` scan cross-checks
the registry against `record.json` discovery: a row with no record anywhere
is a wiped record directory and emits one `error`/`holder_lost` wake with
`state_detail` `record_lost` at fixed `event_seq` 0, marked on the row
(`record_lost_wake`) and deduped by the claims file, so a repeated `status`
reports `already-recovered` and never POSTs again. `status`/`observe`/`send`
on that session return `error.code` `record-lost` with `record_lost` facts
(holder pid, `acp_session_id`, recorded record dir); `list --repo` reports
the loss under `records_lost`; `start` refuses `record-lost-orphan` while the
argv-verified orphan lives; plain `stop` refuses `record-lost`;
`stop --force` sweeps the orphan (argv anchor verified — a reused pid is
never signalled), emits the owed wake, and retires the row; `start --resume`
on the recorded `acp_session_id` is the executable recovery. Contract
coverage: `tests/contract/test-issue-359-record-loss.py` (4 tests). Docs:
`docs/api.md`, `templates/kaola-delegator/references/webhook-wake.md` plus
the rendered `skills/kaola-delegator` copy.

## Candidate

Branch `workflow/issue-359`, one commit on `0df26780` (current main):

- `c251a6f5` Fix #359: durable host registry detects wiped record dirs and
  wakes — `scripts/kaola-acp.py`, `scripts/kaola-acp-holder.py`,
  `scripts/kaola-dispatch.py` (`SWEEP_KAOLA_OWN` gains the two registry
  names), `scripts/kaola-recovery-routes.py`, `scripts/validate.sh`
  (inventory registration), `docs/api.md`, the webhook-wake reference
  (template + rendered copy), `tests/contract/test-issue-359-record-loss.py`,
  regenerated `skills/` hash manifests, `CHANGELOG.md` Unreleased entry
  (`Seats: restart required` — `scripts/kaola-acp-holder.py` is in the
  operator restart set).

Delivered pre-rebase as `350558e9` on the prior main tip; rebased onto
`0df26780` and re-verified as `c251a6f5` (Host acceptance: clean worktree,
route-row regression zero, render PASS).

## Evidence

- `./scripts/render-skills.py --check` -> PASS on `c251a6f5` (11 workers +
  kaola-project-runner + kaola-delegator + grok-bot bridge, content stage,
  `saveable: false`; budgets OK).
- `./scripts/validate.sh --suite` (17 of 135 suites selected) on `c251a6f5`,
  all green in 449 s wall: test-issue-359-record-loss (4 tests),
  test-issue-309-recovery-routes, test-issue-299-delegator-webhook,
  test-issue-325-webhook-outage, test-issue-320-wake-diagnostics,
  test-issue-302-delegator-wake-gate, test-issue-315-decision-wake,
  test-issue-324-wake-fixes, test-issue-76-permission-wake,
  test-issue-92-permission-wake-recovery, test-issue-259-record-contract,
  test-issue-278-record-root, test-issue-292-state-record-root,
  test-issue-293-node-record-roots, test-issue-289-dead-holder-stop,
  test-issue-348-backstop-sweep, test-acp-sweep-contract.
- Recorded at `kaola-workflow/issue-359/.cache/final-validation.md`
  (verdict: pass, bound to the candidate worktree at `c251a6f5`).
- Pre-rebase `350558e9` ran 13 suites all green except
  test-issue-309's residual 7 missing ROUTES rows — a baseline gap already
  fixed on main by #364 (`70602fdf`); that suite passes clean on `c251a6f5`.
- Reproduction at mission 1 used a real holder plus mock-acp-agent and a
  loopback webhook: a wiped record root produced `no-session`, empty `list`,
  and no `holder_lost` wake before the fix.

## Known failures or unverified scope

- None observed on `c251a6f5`.
- The new contract coverage is fixture-backed (synthetic record dirs,
  loopback webhook); no live platform seat was started for this change.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- scripts/kaola-acp-holder.py
- scripts/kaola-acp.py
- scripts/kaola-dispatch.py
- scripts/kaola-recovery-routes.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/antigravity-kaola-project-runner/scripts/kaola-acp.py
- skills/antigravity-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-delegator/references/webhook-wake.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/kaola-delegator/references/webhook-wake.md
- tests/contract/test-issue-359-record-loss.py

## Follow-Up Items

- None. The one run-observed gap (test-issue-309's residual missing ROUTES
  rows) was already fixed on main by #364 (`70602fdf`) before this finalize;
  the suite is green on the candidate. No new defect surfaced.

## Readiness

Candidate `c251a6f5` is accepted by the Host, rebased on current main
`0df26780`, validated at the diff scope, and ready for the merge sink
(sink: merge, issue #359, branch `workflow/issue-359`).
