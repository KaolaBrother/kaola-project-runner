# Finalization Summary — issue-371

## Delivered

An unreadable service manager is no longer reported as an exited job, and its
recovery route converges. Inside a Seatbelt profile `/bin/launchctl list` exits
nonzero; the broker read that as a loaded job, so `do_submit` (both checks),
`do_reconcile`, `_reap_exited_job` and `cleanup` built their message from the
exited route. A session that had never been started was reported as "the job
stays loaded" and "is exited and not owned by this attempt", and the route sent
the same confined caller back to a `reconcile` that refuses identically and to a
`start --resume` with nothing to resume.

Every unknown path now raises one refusal through `unknown_refusal()` carrying
the read's own facts — `os_state: "unknown"`, `manager_rc`, a short
`manager_stderr`, and `caller_confined: true` when `/bin/launchctl` exists but
the read failed — with an `unknown` route that states no job is known to be
loaded or exited and that this is not evidence of a stale job, tells the caller
not to retry from the same confined shell, names the one-shot `reconcile` for an
unconfined shell (`os_state: absent` with `reaped: false` means there was never
a leftover), and names `start`, or `start --resume ID` only when this session's
record carries an `acp_session_id`. The `job-state-unknown` row of
`scripts/kaola-recovery-routes.py` carries the four-step route, `docs/api.md`
states it, and `kaola-acp.py stop` / `kaola-locate.py --intent resume` keep
`os_state` and `caller_confined` in the short `broker_job` fact.

The exited route itself is unchanged: a real exited unowned job is still reaped,
and a real exited job with a live effect still refuses `job-occupied` with the
pre-existing text. Contract coverage:
`tests/contract/test-issue-371-launchd-unreadable.py` (8 tests, registered in
`scripts/validate.sh` lane A).

## Candidate

Branch `workflow/issue-371`, one commit on `e67be3fc` (main at claim time):

- `75199ac2` Fix #371: an unreadable service manager is refused as unknown, not
  as an exited job — `scripts/kaola-launchd-broker.py`, `scripts/kaola-acp.py`,
  `scripts/kaola-locate.py`, `scripts/kaola-recovery-routes.py`,
  `scripts/validate.sh` (inventory registration), `docs/api.md`,
  `tests/contract/test-issue-371-launchd-unreadable.py`, regenerated `skills/`
  copies and hash manifests, `CHANGELOG.md` Unreleased entry.

The candidate is outside the operator restart set
(`git diff OLD NEW -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py
scripts/kaola-quota.py scripts/kaola-record-contract.py scripts/adapters
platforms scripts/kaola-acp-paths.py` is empty for this change), so this change
alone needs no seat restart; the Unreleased section line stays
`Seats: restart required` for the sibling entries that change holder, platform
or quota files.

## Evidence

- Reproduction on `e67be3fc` (before): sandboxed `reconcile`, `submit` and
  `cleanup` for a never-started session all refused `job-state-unknown` with
  "the job stays loaded", "is exited and not owned by this attempt" and a
  `start --resume` route, with no `manager_rc` / `manager_stderr` /
  `caller_confined`; the same command unsandboxed returned
  `{result: reconciled, reaped: false, os_state: absent}`. Recorded at
  <https://github.com/KaolaBrother/kaola-project-runner/issues/371#issuecomment-6270650465>.
- Candidate `75199ac2`: the same sandboxed calls answer `os_state: unknown`,
  `manager_rc: 1`, `manager_stderr: ""`, `caller_confined: true`, contain
  neither false claim, and name the unconfined reconcile plus `start`.
- New suite baseline vs candidate: 5 of 8 cases FAIL on a pre-fix worktree of
  `e67be3fc`; 8 of 8 PASS on `75199ac2`.
- Focused validation on `75199ac2` (clean worktree): `./scripts/validate.sh`
  with `test-issue-371-launchd-unreadable.py`, `test-issue-266-launch-broker.py`,
  `test-issue-266-launch-broker-composed.py`,
  `test-issue-308-resume-reconcile.py`, `test-issue-309-recovery-routes.py`,
  `test-issue-255-lifecycle-state.py` — all PASS, exit 0, 265 s wall.
- Additional route-sensitive suites on the same bytes:
  `test-progressive-disclosure.py`, `test-issue-65-steering.py`,
  `test-issue-289-dead-holder-stop.py`, `test-issue-359-record-loss.py` — all
  PASS, exit 0.
- `./scripts/render-skills.py --check` PASS (11 workers + kaola-project-runner +
  kaola-delegator + grok-bot bridge, content stage, `saveable: false`; budgets
  OK).
- Recorded at `kaola-workflow/issue-371/.cache/final-validation.md`
  (verdict: pass, bound to the candidate worktree at `75199ac2`).
- Host acceptance: the Host personally ran the new suite (8/8 OK) and render
  PASS on `75199ac2`, and confirmed the twelve removed lines are the
  `job-state-unknown` row replacement across its twelve rendered copies.

## Known failures or unverified scope

- None observed on `75199ac2`.
- The new coverage is fixture-backed (`sandbox-exec` plus real one-shot launchd
  jobs the suite boots out); no live platform seat was started for this change.
- The leftover `com.kaolabrother.kaola-runner.launch.484437c481151652` from the
  Issue #120 Seatbelt suite is still loaded on the measuring Mac. This change
  does not cover that suite's job unload, so per the issue's side note it was
  left alone; the new suite boots out every label it bootstraps.

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
- scripts/kaola-launchd-broker.py
- scripts/kaola-locate.py
- scripts/kaola-recovery-routes.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-acp.py
- skills/antigravity-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/antigravity-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/claude-code-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/codex-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/devin-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/droid-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/dsh-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/grok-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/opencode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/zcode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- tests/contract/test-issue-371-launchd-unreadable.py

## Follow-Up Items

- None. No run-discovered defect surfaced beyond the issue's own scope; the
  side-note leftover job was explicitly out of scope unless a cleanup change
  covered it, and this change does not.

## Readiness

Candidate `75199ac2` is accepted by the Host, validated at the diff scope, and
ready for the merge sink (sink: merge, issue #371, branch `workflow/issue-371`).

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-371/.cache/final-validation.md
- kaola-workflow/archive/issue-371/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-371/finalization-summary.md
- kaola-workflow/archive/issue-371/mission-ledger.jsonl
- kaola-workflow/archive/issue-371/workflow-state.md
