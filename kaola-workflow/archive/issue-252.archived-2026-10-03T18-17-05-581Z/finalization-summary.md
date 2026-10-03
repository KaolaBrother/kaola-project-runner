# Issue 252 finalization summary

## Delivered

The dispatch entry now prefers spreading useful breadth work across fitting Worker presets, and an explicit Expert grant may carry `lifetime` and `expires`. Rejected re-execution keeps correlation and records only the reason on `evidence.blocked_attempt`. No Expert grant was inferred for this run. Budgets 17408 and 8192 are unchanged. `execute` stays limited to research, QA, and report.

## Candidate

Candidate: `72c027b2589574dda8eb7134e5e4c321d8b124e0`
Parent: `5763b047248ccd7f898ec1eb6b63d615044c0055`
Subject: `feat: spread breadth work and add standing Expert grants (#252)`
Branch: `workflow/issue-252`
Worktree: `/Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-252`
Baseline main at acceptance: `987022949d55784c4e0a4138ca3a159315311e85`

The worktree was clean at that commit. The Host accepted this candidate after the joint review found no blocking defect. That acceptance is not issue closure. No source amendment was made for finalization.

## Evidence

Writer note `/tmp/kpr-i252-writer.md` sha256 `5b96203d191b0ed74bc3e0fde204a9d3bd0cc1d38d4356b4aabb3767f5cca5ee`.
Validation log `/tmp/kpr-i252-writer-validate.log` sha256 `50dfebed737dddb3cc12b7384810fc3f50f38cdb4c25ce15dffb4bd667157784`, 73925 bytes, mtime `2026-10-04T01:30:12+0800`. The log ends `validate rc=0` and includes `render-skills: PASS` plus the Grok Bot content-stage line. The commit time is `2026-10-04T01:30:25+08:00`. The log does not embed the commit hash. The exact command recorded from the writer note is `./scripts/validate.sh`. The Host did not rerun that suite.
Joint review `/tmp/kpr-i252-joint-review.md` sha256 `a6475c588768636f5e46361f05904883ec188e39138af745c55dee220334b316`. Session `claude-code-KPR-i252-joint` is stopped: `agent_exit_code` 0, signal none, residual `[]`. Do not resume holder `44f2e5a495d95c0dca8321309fd8b51d`.
Complementary QA notes, each judged with no concrete blocking defect and none of them issue acceptance: `/tmp/kpr-i252-qa-grants.md`, `/tmp/kpr-i252-qa-wording.md`, `/tmp/kpr-i252-qa-evidence.md`, `/tmp/kpr-i252-qa-admission.md`.
The script diff against the parent does not contain `blocked_attempt` or `def publish`. Both revisions still have the one write site.

## Known failures and unverified scope

No blocking failure remains on this candidate. The pre-existing `publish()` stamp is follow-up #253.
The Host did not independently rerun `./scripts/validate.sh`, the full contract suite, or Python 3.10. The reviewer's hand probes of `lifetime-unreadable`, fresh `revoked`, and a standing Expert projection are not suite evidence. No live Expert session ran. No token or cost saving is claimed. E1 locators predate this commit and prove an earlier tree only. Installation was not performed and is not authorized. The Grok Bot bridge on this candidate is still stage `content`, 2555 bytes, unpinned. The operator diff from `v0.7.0` to this commit is non-empty, so the release section must say `Seats: restart required`. That line is part of cutting the release.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- README.md
- docs/acp-watch/follow.md
- docs/acp-watch/list-view.md
- docs/api.md
- docs/dispatch-collect.md
- platforms/claude-code.yaml
- platforms/codex.yaml
- platforms/devin.yaml
- scripts/kaola-acp-holder.py
- scripts/kaola-acp.py
- scripts/kaola-dispatch.py
- scripts/kaola-tmux.sh
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-tmux.sh
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/platform.yaml
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-tmux.sh
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/platform.yaml
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-tmux.sh
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-tmux.sh
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/platform.yaml
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-tmux.sh
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-tmux.sh
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-tmux.sh
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-delegator/SKILL.md
- skills/kaola-delegator/references/snapshot.md
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/dispatch-collect.md
- skills/kaola-project-runner/references/duty-reconcile.md
- skills/kaola-project-runner/references/heartbeat-skeleton.md
- skills/kaola-project-runner/references/profile-catalog.md
- skills/kaola-project-runner/references/public-research.md
- skills/kaola-project-runner/references/qa-evidence.md
- skills/kaola-project-runner/references/worker-profiles.md
- skills/kaola-project-runner/references/zcode-host-dispatch.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-tmux.sh
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-tmux.sh
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-tmux.sh
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/kaola-delegator/SKILL.md.tmpl
- templates/kaola-delegator/references/snapshot.md
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/dispatch-collect.md
- templates/orchestrator/references/duty-reconcile.md
- templates/orchestrator/references/heartbeat-skeleton.txt
- templates/orchestrator/references/public-research.md
- templates/orchestrator/references/qa-evidence.md
- templates/orchestrator/references/worker-profiles.md.tmpl
- templates/orchestrator/references/zcode-host-dispatch.md.tmpl
- tests/contract/test-issue-244-dispatch.py
- tests/contract/test-issue-245-session-role.py

## Follow-Up Items

- filed: #253. Confirmed OPEN, title `publish() can stamp blocked_attempt reason missing before the executor`, labels `bug` and `P2`, body 2512 bytes and non-empty. It does not block this candidate.
- Not filed: `docs/architecture.md:31` and `docs/zcode-host.md:376` still say Expert presets need fresh per-task permission. The reviewer reported this. Those files are outside the design's required generated surfaces.
- Not filed: an `expires` offset written as `+0800` without a colon is accepted on Python 3.12 and would fail closed as `expiry-unreadable` on Python 3.10. Trailing `Z` on Python 3.10 was not verified. `lifetime` is a label, not an admission rule. `--seats` echoes `lifetime` and `expires` on any grant row. `turn_facts` can report `turn_outcome` `stopped`. None of these blocked the review.

## Readiness

Ready for the finalize transaction. The historical archive `kaola-workflow/archive/issue-252/` stays in place. The four untracked harness docs stay untracked. After publication, cut the next release under the existing conventions, including the Seats line and the Grok Bot pin. Do not install. Keep the Delegator timer ACTIVE.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-codex-160-live-2026-10-03.md
- docs/harness-acp-compat-2026-10-01.md
- docs/harness-acp-compat-2026-10-03.md
- docs/harness-acp-reverify-2026-10-01.md

## Sink Findings

post_rebase_tests: skipped

archive_collision: kaola-workflow/archive/issue-252/ already existed, so this run was archived to kaola-workflow/archive/issue-252.archived-2026-10-03T18-17-05-581Z/ instead. The pre-existing directory was left exactly where it was — a SECOND archive standing for this project, no part of this one. What it holds, and whether the repository tracks it at all, is not recorded here: read it before treating this archive as the run's whole record.

archived_paths:
- kaola-workflow/archive/issue-252.archived-2026-10-03T18-17-05-581Z/.cache/final-validation.md
- kaola-workflow/archive/issue-252.archived-2026-10-03T18-17-05-581Z/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-252.archived-2026-10-03T18-17-05-581Z/finalization-summary.md
- kaola-workflow/archive/issue-252.archived-2026-10-03T18-17-05-581Z/mission-ledger.jsonl
- kaola-workflow/archive/issue-252.archived-2026-10-03T18-17-05-581Z/qa/sideagent/archive-before.json
- kaola-workflow/archive/issue-252.archived-2026-10-03T18-17-05-581Z/qa/sideagent/bytes.json
- kaola-workflow/archive/issue-252.archived-2026-10-03T18-17-05-581Z/qa/sideagent/bytes.md
- kaola-workflow/archive/issue-252.archived-2026-10-03T18-17-05-581Z/qa/sideagent/candidate-commit.txt
- kaola-workflow/archive/issue-252.archived-2026-10-03T18-17-05-581Z/qa/sideagent/candidate-files-after.json
- kaola-workflow/archive/issue-252.archived-2026-10-03T18-17-05-581Z/qa/sideagent/candidate-files-before.json
- kaola-workflow/archive/issue-252.archived-2026-10-03T18-17-05-581Z/qa/sideagent/consumer-consistency.md
- kaola-workflow/archive/issue-252.archived-2026-10-03T18-17-05-581Z/qa/sideagent/host-review.md
- kaola-workflow/archive/issue-252.archived-2026-10-03T18-17-05-581Z/qa/sideagent/interrupted-finalization.md
- kaola-workflow/archive/issue-252.archived-2026-10-03T18-17-05-581Z/qa/sideagent/owner-correction-issue.json
- kaola-workflow/archive/issue-252.archived-2026-10-03T18-17-05-581Z/qa/sideagent/preservation-check.json
- kaola-workflow/archive/issue-252.archived-2026-10-03T18-17-05-581Z/qa/sideagent/render-check.exit
- kaola-workflow/archive/issue-252.archived-2026-10-03T18-17-05-581Z/qa/sideagent/render-write-initial.exit
- kaola-workflow/archive/issue-252.archived-2026-10-03T18-17-05-581Z/qa/sideagent/render-write.exit
- kaola-workflow/archive/issue-252.archived-2026-10-03T18-17-05-581Z/qa/sideagent/resume.json
- kaola-workflow/archive/issue-252.archived-2026-10-03T18-17-05-581Z/qa/sideagent/same-native-resume-focused.exit
- kaola-workflow/archive/issue-252.archived-2026-10-03T18-17-05-581Z/qa/sideagent/session-role-focused-initial.exit
- kaola-workflow/archive/issue-252.archived-2026-10-03T18-17-05-581Z/qa/sideagent/session-role-focused.exit
- kaola-workflow/archive/issue-252.archived-2026-10-03T18-17-05-581Z/qa/sideagent/skip-summary.json
- kaola-workflow/archive/issue-252.archived-2026-10-03T18-17-05-581Z/qa/sideagent/skips.txt
- kaola-workflow/archive/issue-252.archived-2026-10-03T18-17-05-581Z/qa/sideagent/validate-interrupted.txt
- kaola-workflow/archive/issue-252.archived-2026-10-03T18-17-05-581Z/qa/sideagent/validate.exit
- kaola-workflow/archive/issue-252.archived-2026-10-03T18-17-05-581Z/workflow-state.md
