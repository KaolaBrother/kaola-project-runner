# Finalization Summary — issue-344

## Delivered

Issue #344: a `start` that carries a brief (`--stdin` or `--text`) delivers that brief as the
session's first prompt turn, and reports `ready` only after that turn has actually started.
Verified success carries `turn_request_id`, that turn's `prompt_fingerprint`, and
`brief_delivered=true`. Delivery or turn-start that cannot be verified is not ready-as-dispatched:
`brief_delivered=false`, a typed reason or refusal, and a non-zero exit. A ready receipt with no
turn is not dispatch evidence.

`--no-wait` waits only for admission and turn start. A start with no brief is unchanged. Empty
brief text is refused before spawn (`brief-empty`). `kaola-dispatch.py` `execute` stays
start-with-no-brief, then `send --no-wait` as the first turn. Docs, Runner Skill templates, and
the kaola-delegator handoff match that contract. Generated `skills/` and `hosts/grok-bot/` come
from `./scripts/render-skills.py --write`. The grok-bot bridge stays content-stage and unpinned.

Issue #72's startup-example pin now requires one exact session name across
`start --no-wait --text`, `observe`, `capture`, and `stop`. The example no longer shows a second
`send` of the same brief.

## Candidate

Branch `workflow/issue-344`, based on local `main` `4e64baa4`.

- `7a6a1dfc` — `fix: deliver a start brief as the first verified prompt turn (#344)`
- `994d2ce8` — `fix: pin the startup example to one start-brief name (#344, #72)`

Acceptance candidate: `994d2ce8`. Not pushed.

Host acceptance: ACCEPTED. The pre-merge full gate on this commit is green.

## Evidence

- Full inventory `./scripts/validate.sh` (no `--suite`), worktree clean at `994d2ce8`: 123 suites,
  exit 0, wall 1488.62 s. Log: `/tmp/kpr-run/full-validate-344-994d2ce8-r2.log`
  (`VALIDATE_EXIT=0`). `render-skills: PASS` is inside that run.
- An earlier full-gate round failed only `test-issue-341-agent-initiated-turn.py`. Host judged
  that a timing flake by a single rerun and by comparison with round 1. This round's same suite
  passed (`validate: elapsed test-issue-341-agent-initiated-turn.py 27.301 s`). Not an open defect.
- Focused evidence already on the candidate, before the full gate: render `--write` and `--check`
  exit 0; `validate.sh` of test-issue-72, test-issue-344, and test-issue-264 exit 0. Log:
  `/tmp/kpr-344-pin72.log`.
- Fail-on-main voucher, unfixed `4e64baa4`: `/tmp/kpr-repro-344/fail-on-4e64baa4.txt` (`EXIT:1`,
  10 failures).

## Known failures and unverified scope

- No known product failure on `994d2ce8`.
- Host boundary for this finalize: merge into local main only. Do not push. Do not close issue
  #344. Do not add a GitHub comment. Do not release, tag, install, or open a new issue.
  Keep-open is that deferral. Offline mode makes no forge call, so the claim label is not
  released here.
- Post-merge `./scripts/render-skills.py --write` and `--check` run on local main after the sink.
  No validate suite is re-run; the full gate already passed on this same commit.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- docs/dispatch-collect.md
- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- scripts/kaola-acp.py
- scripts/kaola-recovery-routes.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/SKILL.md
- skills/antigravity-kaola-project-runner/references/acp.md
- skills/antigravity-kaola-project-runner/scripts/kaola-acp.py
- skills/antigravity-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/SKILL.md
- skills/claude-code-kaola-project-runner/references/acp.md
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/SKILL.md
- skills/codex-kaola-project-runner/references/acp.md
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/SKILL.md
- skills/cursor-cli-kaola-project-runner/references/acp.md
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/SKILL.md
- skills/devin-kaola-project-runner/references/acp.md
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/SKILL.md
- skills/droid-kaola-project-runner/references/acp.md
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/SKILL.md
- skills/dsh-kaola-project-runner/references/acp.md
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/SKILL.md
- skills/grok-kaola-project-runner/references/acp.md
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-delegator/references/handoff.md
- skills/kaola-delegator/references/host-restart.md
- skills/kaola-project-runner/references/dispatch-collect.md
- skills/kaola-project-runner/references/host-startup.md
- skills/kaola-project-runner/references/zcode-host-dispatch.md
- skills/kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/SKILL.md
- skills/kimi-cli-kaola-project-runner/references/acp.md
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/SKILL.md
- skills/opencode-kaola-project-runner/references/acp.md
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/SKILL.md
- skills/zcode-kaola-project-runner/references/acp.md
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/SKILL.md.tmpl
- templates/grok-bot/accepted-revision.json
- templates/kaola-delegator/references/handoff.md.tmpl
- templates/kaola-delegator/references/host-restart.md
- templates/orchestrator/references/dispatch-collect.md
- templates/orchestrator/references/host-startup.md.tmpl
- templates/orchestrator/references/zcode-host-dispatch.md.tmpl
- templates/references/acp.md.tmpl
- tests/contract/test-issue-344-start-brief.py
- tests/contract/test-issue-72-session-naming.py

## Follow-Up Items

None. The #341 timing flake was accepted by the Host on the green full gate. No follow-up issue.

## Readiness

Ready to merge `workflow/issue-344` at `994d2ce8` into local main and archive this run.
Issue #344 stays open.

## Finalize Findings

### claim_release_skipped_offline

This finalize released no claim: KAOLA_WORKFLOW_OFFLINE=1, so the release returned before making any forge call. Nothing local records whether this run was ever claimed online, so this does not assert the artifacts are there — but IF the claim was posted, the `workflow:in-progress` label and the `kw:claim` marker comment are still on the issues below. The marker expires after 24h; the label does not, and either one blocks a later claim of that issue until it is removed.

Issues whose claim release was skipped:

- #344

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-344/.cache/final-validation.md
- kaola-workflow/archive/issue-344/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-344/finalization-summary.md
- kaola-workflow/archive/issue-344/mission-ledger.jsonl
- kaola-workflow/archive/issue-344/workflow-state.md
