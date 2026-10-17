# Finalization Summary — issue-335

## Delivered

Issue #335: a kimi-cli `turn_failed` now stores a bounded, redacted provider-error
summary on `turn_ended.error` and on `record.json` / op-state `turn_error`.

- Usable ACP error text is kept, including a holder string code such as
  `agent-system-error`. Empty text and `[object Object]` on kimi-cli are filled
  from that session's `agents/main/wire.jsonl` (latest `provider.*` / `auth.*`
  error). Credentials are redacted and the message is capped.
- A missing, unreadable, or error-free wire degrades to
  `provider-error-unavailable` / "no provider error available" and does not
  invent an error. `fatal_error` stays a start/resume field. A later non-failed
  turn clears `turn_error`.
- The #309 recovery table now routes the three extracted readback codes:
  `provider-error-unavailable`, `wire-missing`, and `wire-unreadable`. Existing
  codes are unchanged.

## Candidate

Branch `workflow/issue-335`, commit `e3d5db8c`
(`fix(routes): register kimi provider-error readback codes (#335)`),
fast-forward from local main `af007f90`. Parent implementation commit
`f177c53f` (`fix(holder): carry kimi provider errors on turn_failed (#335)`).
Not pushed.

Host acceptance: ACCEPTED. The pre-merge whole-inventory gate on this exact
commit is green.

## Evidence

- Whole-inventory `./scripts/validate.sh` on candidate `e3d5db8c` (clean):
  122 suites, exit 0, wall 1563.19 s.
  Log: `/tmp/kpr-run/full-validate-335-e3d5db8c.log` (`VALIDATE_EXIT=0`).
- Recorded validation (`.cache/final-validation.md`) binds this worktree to
  that command. The gate is not rerun here; the candidate bytes are unchanged.
- Earlier focused evidence remains on the implementation commit and is
  superseded for acceptance by this whole-inventory result.

## Known failures and unverified scope

- No known product failures.
- Host boundary for this finalize: merge into local main only. Do not push.
  Do not close or comment on issue #335. Do not release, tag, install, or open
  a new issue. Keep-open is that deferral, not leftover product scope.
- Post-merge `./scripts/render-skills.py --write` and `--check` run on local
  main after the sink. No validate suite is run again.
- The grok-bot bridge stays at the unpinned content stage. The next release
  owns the pin.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- scripts/kaola-acp-holder.py
- scripts/kaola-recovery-routes.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/antigravity-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- tests/contract/test-issue-335-kimi-provider-error.py

## Follow-Up Items

- None filed. No run-discovered defect requires a new issue. `searched:` not
  applicable; nothing was filed.

## Readiness

Host accepted the change. Validation is recorded pass on `e3d5db8c`. Local
merge-sink and archive proceed. Issue #335 stays open. Publication to the
remote waits for the Host.

## Finalize Findings

### claim_release_skipped_offline

This finalize released no claim: KAOLA_WORKFLOW_OFFLINE=1, so the release returned before making any forge call. Nothing local records whether this run was ever claimed online, so this does not assert the artifacts are there — but IF the claim was posted, the `workflow:in-progress` label and the `kw:claim` marker comment are still on the issues below. The marker expires after 24h; the label does not, and either one blocks a later claim of that issue until it is removed.

Issues whose claim release was skipped:

- #335

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-335/.cache/final-validation.md
- kaola-workflow/archive/issue-335/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-335/finalization-summary.md
- kaola-workflow/archive/issue-335/mission-ledger.jsonl
- kaola-workflow/archive/issue-335/workflow-state.md
