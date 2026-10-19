# Finalization Summary — issue-369

## Delivered

A worktree is never removed under a live shell cwd, and a host whose bash tool
kept its cwd inside a removed worktree is repaired in place instead of losing
every later shell call.

The shared probe `scripts/kaola-cwd-guard.py` answers `clear` / `occupied` /
`unverifiable` for one target from the caller's process chain and every live
session tree, with a recorded `tool_cwd.last_known` as an occupant even when no
process holds it. `kaola-dispatch.py worktree-remove` is the one guarded
removal (relocate own cwd, defer on `occupied`/`unverifiable` with a route,
repair the check-then-delete race into an empty placeholder, `--assume-clear`
covers only the unreadable probe); `worktree-guard` is its read-only form, and
the backstop sweep plans and removes through the same wrapper. The holder
records its own agent's tool cwd (manifest note regex, tier B; a rate-limited
shell-only descendant sample, tier C), reacts to V1/V2/V3, creates an empty
placeholder per removed path, stages one notice per path (steer while a turn
runs, otherwise the next idle worker-event prompt), cleans up when the shell
leaves or at exact stop, and reconciles claims on boot and resume. Six recovery
rows (`tool-cwd-vanished`, `tool-cwd-unknown`, `cwd-occupied`,
`cwd-unverifiable`, `cwd-repair-failed`, `cwd-placeholder-not-empty`) plus the
wrapper's `cwd-relocate-failed` carry the operator routes.

Review repairs on top of the first candidate:

- Round 2 (Expert implementation review): tier C accepts only shell
  descendants (no observation, never a stale overwrite, when no shell lives);
  V3 and repair require the target to be gone (no false "deleted" notice for a
  live path); resume restores `tool_cwd` before reconciliation; placeholder
  claims are a set, notice dedupe is per path, vanish events are per path, an
  unreadable `git worktree list` is a recorded duty, a failed removal's detail
  carries stderr, `tool-cwd-unknown` has a real emission point, the
  unavailable-probe case is platform-aware, and the prompt-path worktree
  refresh moved to a boot baseline to close a same-thread lock re-entry.
- Round 3 (Expert re-review, no blocking findings): a fresh start inherits
  only placeholder claims, never a stale `last_known` (R2-1); the worktree
  probe is three-state and an unknown answer keeps the claim instead of
  dropping it as "registered again" (R2-2).

## Candidate

Branch `workflow/issue-369` (base `e67be3fc`, main at claim time):

- `c4b9f19b` Never remove a worktree under a live shell cwd (#369)
- `c60c0a68` Guard every worktree removal and repair a vanished tool cwd (#369)
- `9b37304d` Fix the #369 cwd watch review findings (round-2 B/N items)
- `ffacb90c` Inherit only a placeholder claim on a fresh start (#369) (R2-1/R2-2)
- `ddc5cb27` Merge origin/main (`a5af6a97`) into `workflow/issue-369`; the
  sink's own rebase conflicted on the shared CHANGELOG/docs/route rows and
  main-skill manifests. The resolution keeps main's #371/#368 rows and the
  branch's #369 rows; rendered copies were regenerated with
  `render-skills.py --write`.

The changed surface is `scripts/kaola-cwd-guard.py`,
`scripts/kaola-dispatch.py`, `scripts/kaola-acp-holder.py`,
`scripts/kaola-acp.py`, `scripts/kaola-recovery-routes.py`,
`platforms/zcode.yaml`, the orchestrator/Delegator guidance, docs, CHANGELOG,
the three #369 contract suites, the mock `cwd_vanish` scenario, `validate.sh`
registration, and regenerated `skills/` copies plus hash manifests.
`scripts/kaola-acp-holder.py` and `platforms/zcode.yaml` are in the operator
restart set, so the Unreleased line is `Seats: restart required`.

## Evidence

- Reproduction on the pre-fix tree (measured): the persistent shell's cwd left
  inside a removed worktree makes every later call fail with
  `spawn /bin/zsh ENOENT` while `/bin/zsh` exists; the backstop sweep's real
  keep decision allowed that removal. Recorded at
  <https://github.com/KaolaBrother/kaola-project-runner/issues/369#issuecomment-6267756717>.
- Expert design round 1: <https://github.com/KaolaBrother/kaola-project-runner/issues/369#issuecomment-6268020291>
  (measured wire facts, detector tiers, repair/notice/cleanup semantics).
- Round-2 review findings: the B-1/B-2/B-3 blocking items plus N-1/N-2/N-3/N-5
  and deviations b/d/e, all closed in `9b37304d`; the round-3 re-review passed
  with no blocking findings and the deadlock fix recorded as an improvement.
- Contract suites at `ffacb90c`: `test-issue-369-worktree-guard.py` 6/6,
  `test-issue-369-holder-cwd-repair.py` 18/18 (1 skipped: tier A/D1),
  `test-issue-369-cwd-vanished.py` 4/4, `test-issue-309-recovery-routes.py`
  8/8, all PASS through `./scripts/validate.sh --suite ...`, exit 0, 94.991 s;
  render-check and validate-skill PASS; `render-skills.py --check` PASS.
- Validation receipt: `.cache/final-validation.md` (verdict: pass, bound to
  the pre-merge candidate tree `ffacb90c`). After the `origin/main` merge the
  same affected suites were re-run on `ddc5cb27` (see below); main's own
  content had already been validated by its run, and the branch's changed
  bytes are unchanged by the merge.
- Post-merge revalidation on `ddc5cb27` (clean worktree): the same
  `./scripts/validate.sh --suite ...` set — holder 18/18 (1 skipped),
  worktree-guard 6/6, cwd-vanished 4/4, recovery-routes 8/8, render-check and
  validate-skill PASS, exit 0, 91.802 s.

## Known failures or unverified scope

- Tier C is a rate-limited live sample: it misses short or never-started shell
  calls, and tier A (runner-owned `ZDOTDIR`/`BASH_ENV` entry) remains
  unadopted (D1 open). On a platform without tier B, an unknown `last_known` at
  removal time relies on the V2 pre-emptive placeholder + notice (D3, accepted
  default). `/bin/sh` tools have no tier A entry hook.
- `tool_cwd_repair_error` is a single status slot: with several simultaneous
  repair duties only the latest is shown; the event log keeps each one.
- The steer notice names one path per delivery: with several repaired paths the
  steer carries the latest text; the other notices ride the idle worker-event
  batch. A fresh start reconciles claims but does not re-deliver a previous
  session's notice (resume does).
- No live ZCode smoke was re-run in the review repair rounds; the change is
  covered by the mock-ACP contract suites and render, and live smoke remains
  the integration boundary. No install/restart was performed.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to the pre-merge candidate `ffacb90c`;
post-merge revalidation on `ddc5cb27` re-ran the same affected suites green

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- platforms/zcode.yaml
- scripts/kaola-acp-holder.py
- scripts/kaola-acp.py
- scripts/kaola-cwd-guard.py
- scripts/kaola-dispatch.py
- scripts/kaola-recovery-routes.py
- scripts/render-skills.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/antigravity-kaola-project-runner/scripts/kaola-acp.py
- skills/antigravity-kaola-project-runner/scripts/kaola-cwd-guard.py
- skills/antigravity-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-cwd-guard.py
- skills/claude-code-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-cwd-guard.py
- skills/codex-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-cwd-guard.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-cwd-guard.py
- skills/devin-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-cwd-guard.py
- skills/droid-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-cwd-guard.py
- skills/dsh-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-cwd-guard.py
- skills/grok-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-delegator/references/host-brick.md
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/workflow-worktree.md
- skills/kaola-project-runner/scripts/kaola-cwd-guard.py
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-cwd-guard.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-cwd-guard.py
- skills/opencode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-cwd-guard.py
- skills/zcode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/platform.yaml
- templates/kaola-delegator/references/host-brick.md
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/workflow-worktree.md
- tests/contract/mock-acp-agent.py
- tests/contract/test-issue-369-cwd-vanished.py
- tests/contract/test-issue-369-holder-cwd-repair.py
- tests/contract/test-issue-369-worktree-guard.py
- tests/contract/test-progressive-disclosure.py

## Follow-Up Items

- None filed. The residuals above are accepted design boundaries recorded here
  (tier C/D1 cost, single repair-error slot, one-path steer notice); no new
  run-discovered defect surfaced in the review repair rounds.

## Readiness

Candidate `ffacb90c` is accepted by the Host (two Expert review rounds, no
blocking findings) and validated at the affected diff scope; ready for the
merge sink (sink: merge, issue #369, branch `workflow/issue-369`).

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-369/.cache/final-validation.md
- kaola-workflow/archive/issue-369/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-369/finalization-summary.md
- kaola-workflow/archive/issue-369/mission-ledger.jsonl
- kaola-workflow/archive/issue-369/workflow-state.md
