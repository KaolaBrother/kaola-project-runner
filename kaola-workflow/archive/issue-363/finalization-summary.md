# Finalization Summary — issue-363

## Delivered

A `start --resume`/`--continue` receipt for dsh now reports the permission the
resumed session actually keeps instead of claiming the launch variable applied.
dsh pins `permission/preset`, `sandbox/mode`, and `approval/policy` into its
session log at creation and restores them on `session/resume`, so
`DSH_PERMISSION_MODE` carried by a resume never changes them. The mode receipt
now reports `{"applied": false, "requested_via": "env", "value", "source",
"reason": "resumed-session-permission"}` plus `effective` — the session's own
recorded `preset`/`sandbox`/`approval`/`session_log` with
`effective_via: "session-log"` — when the log under `$DSH_HOME/sessions/` is
readable (plain or zstd), and no `effective` when it is not. Fresh starts keep
`applied: true, applied_via: "env"`; the drain-restart mode echo prefers the
recorded `effective.preset`. The session-store directory key mirrors dsh's
`projectKey`/`encodeSegment` and resolves the repo path first (dsh records the
resolved cwd). `resumed-session-permission` gained a `route` row in
`scripts/kaola-recovery-routes.py`, and the Delegator host-restart guide, the
dsh `permission_summary`, `docs/api.md`, and `docs/architecture.md` state that
a session born confined needs a fresh session to gain a wider preset.

## Candidate

Branch `workflow/issue-363`, one commit `e7833ff1` on main `c84741fe` (rebased
after the first delivery so the re-rendered generated copies keep #364's
recovery-route rows intact).

## Evidence

- Reproduction (pre-fix): mock ACP fixture — a workspace-write-born session
  resumed under the Runner default reported `applied: true`,
  `value: danger-full-access`, while `inherited_start_evidence` showed the
  `workspace-write` birth claim.
- Contract suite `tests/contract/test-issue-363-dsh-resume-permission.py`:
  10 tests covering fresh-start apply, confined-birth resume receipt, latest
  event wins, absent/unreadable log stays without `effective`, full-birth
  resume, zstd log decode, session-store naming (incl. the symlink/realpath
  case), and path-segment encoding.
- `./scripts/validate.sh --suite test-issue-363-dsh-resume-permission.py
  --suite test-issue-98-dsh-acp.py --suite test-issue-308-resume-reconcile.py
  --suite test-issue-316-resume-model-evidence.py --suite
  test-issue-162-upgrade-safety.py --suite test-issue-345-dsh-commandcode.py
  --suite test-issue-351-dsh-profile.py --suite
  test-issue-309-recovery-routes.py` → all lanes PASS, 113 tests OK, exit 0.
- `./scripts/render-skills.py --check` → PASS (content stage, budgets OK).
- Live dsh 0.2.1-rc.2 smoke on a fresh session `833c92b4`: born
  `DSH_PERMISSION_MODE=workspace-write` (receipt `applied: true,
  workspace-write, caller-env`); real log
  `~/.dsh/sessions/--private-tmp-i363-live-repo--/833c92b4…/session.v4.jsonl.zstd`
  pinned `workspace-write`/`workspace-write`/`ask`; stopped; resumed under the
  Runner default → `applied: false`, `reason: resumed-session-permission`,
  `effective` = the recorded `workspace-write`/`workspace-write`/`ask` via
  `session-log`, request `danger-full-access`/`runner-default` kept as
  `value`/`source`. Smoke session stopped and its session dir plus the temp
  repo/records removed.
- Recorded receipt: `kaola-workflow/issue-363/.cache/final-validation.md`
  (verdict pass, bound to the worktree hash).
- Host acceptance: the operator confirmed the rebase (zero recovery-route line
  regression), re-ran the 10-test suite green, and verified the live smoke
  evidence end to end.

## Known failures or unverified scope

- The 133-suite full inventory was not run on this candidate; the focused
  suites plus render check were the agreed scope and the Host runs the full
  inventory at its own boundary.
- `docs/` and receipt-shape consumers see the new `mode` fields; readers that
  assumed `applied: true` on resume now see the honest `applied: false`.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- docs/architecture.md
- platforms/dsh.yaml
- scripts/kaola-acp.py
- scripts/kaola-recovery-routes.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-acp.py
- skills/antigravity-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/SKILL.md
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/platform.yaml
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-delegator/references/host-restart.md
- skills/kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/kaola-delegator/references/host-restart.md
- tests/contract/test-issue-363-dsh-resume-permission.py

## Follow-Up Items

Filed: #370 — `missing-host-holder-instance-id` lacks a `kaola-recovery-routes.py`
row on main (pre-existing gap from #365, found on the post-rebase audit; this
run's own `resumed-session-permission` row already lands in the same table).
The two rework findings in-scope for #363 (the recovery-route audit row and the
realpath key fix) landed inside this change with regression coverage.

## Readiness

Ready for merge-sink close-out. `Seats: restart required` — the diff touches
`platforms/dsh.yaml`, which is in the operator restart set
(`docs/conventions.md`); a running seat keeps the previous permission summary
text until it restarts.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-363/.cache/final-validation.md
- kaola-workflow/archive/issue-363/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-363/finalization-summary.md
- kaola-workflow/archive/issue-363/mission-ledger.jsonl
- kaola-workflow/archive/issue-363/workflow-state.md
