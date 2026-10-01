# Issue 240 — Delegate substantial thinking and parallel exploratory QA

## Delivered

The Host entry now lets helpers plan and design, and it delegates substantial planning, design, or review to an available authorized seat when that seat's profile or the owner's task-specific judgment fits better than the Host's own known model/preset. Clear tasks still go directly to a suitable authorized worker. Independent parts split or parallelize when they gain real time or coverage; the count remains a ceiling, and the no-invented-work and stop-before-start guards stay.

Worker Class is simpler, bounded work, mirrored in the README class row. `claude-code/opus-xhigh` plans, designs, and reviews but does not implement; a Claude Code Host still plans, dispatches, and accepts. The choosing rule forbids a universal model ranking and does not add a ranking mechanism.

QA evidence says a better-fitting authorized seat may draft the plan while the verdict stays with the Host. Exploratory checks and heavy or long-running test runs prefer suitable available Worker-Class seats by profile fit, with a fitting authorized Elite when they lack a needed capability. Parallel checks need distinct scopes and non-interfering state. A return names anything not executed or explored. The main entry tells the Host to read `qa-evidence.md` before planning, assigning, or judging QA unless that current version is already in context.

No release, tag, install, or CHANGELOG release section. Byte ceilings were not raised. `#207`/`#216` account and limit rules and `#238` task-failure policy are unchanged. The heartbeat skeleton is unchanged. Because this checkout was the v0.6.15 pin, `templates/grok-bot/accepted-revision.json` returned to the content stage so the renderer could write; generated `hosts/grok-bot/` matches content commit `96a05fdf` and is not saveable.

## Candidate

4cb197f8bf9e1eea2ef854bc8fc86b9f92a466e5, workflow/issue-240.
Worktree: /Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-240
Baseline: 5d649a80. Diff: 23 files, +132/−114.

## Evidence and acceptance

Host ACCEPTANCE: PASS. The Host verified E1–E8 on the actual diff, the strengthened QA pointer at `SKILL.md:204-206`, untouched `#207`/`#216`/`#238` and heartbeat skeleton, and an honest content-stage transition.

Host independent byte check, matching this candidate:
- Host entry `skills/kaola-project-runner/SKILL.md` 16466 B (+318 = agreed eight-edit +220 plus QA pointer +98; ceiling 17408; headroom 942)
- `references/worker-profiles.md` 8074 B (+32; ceiling 8192; headroom 118)
- `references/qa-evidence.md` 6846 B (+445; ceiling 8192; headroom 1346)
- `references/heartbeat-skeleton.md` 7866 B (+0; ceiling 8192; headroom 326)

Host QA real-read, recorded by the Host for this candidate:
- path: `.kw/worktrees/issue-240/skills/kaola-project-runner/references/qa-evidence.md`
- sha256: `08dd437546bd385205c2d47cf88eb5bf0dd79c6a95bfd1d41c53359c4944948f`
- bytes: 6846
- worktree HEAD at that read: `5d649a80` (the pin parent; the same file bytes are in delivery commit `4cb197f8`, sha256 unchanged)
- the applied QA plan follows that reference: Host is the sole quality owner; reuse-first for this text-only change; the worker battery plus Host independent reruns are the checks; no Worker-Class exploration, because no unknown exploratory route exists for deterministic prompt edits
- QA VERDICT: PASS for this candidate scope

Host independent `./scripts/render-skills.py --check`: PASS. Worker affected-check battery, same bytes, all green: progressive-disclosure (15 OK), test-issue-41 (23 OK), generated-skills PASS, test-issue-218 (16 OK), test-issue-65-host-contract (13 OK), test-zcode-host-contract (3/3, 48 checks), test-issue-119-host-entry (11/11, 164 checks), test-issue-68-heartbeat-snapshot (8 OK), test-issue-49-grok-bot-host (45 OK).

`run-chains --project issue-240` from this worktree: exit 1, `chains_config_missing` — this repo has no `package.json` `test:kaola-workflow:*` scripts. Consumer finalize evidence is `.cache/final-validation.md`.

This record has no complete `./scripts/validate.sh` receipt, so it does not call that suite green.

Protected files, including untracked `docs/harness-acp-compat-2026-10-01.md` and `docs/harness-acp-reverify-2026-10-01.md`, were not staged or deleted.

## Known failures or unverified scope

No failure on this candidate. No release, tag, install, or CHANGELOG release section. `main-skill-build.json` hashes changed with the Host entry; this run did not reinstall. Repository-candidate validation does not claim the installed release changed.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- README.md
- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- scripts/render-skills.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/qa-evidence.md
- skills/kaola-project-runner/references/worker-profiles.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/grok-bot/accepted-revision.json
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/qa-evidence.md
- templates/orchestrator/references/worker-profiles.md.tmpl
- tests/contract/test-issue-218-preset-ids.py

## Follow-Up Items

None. No run-discovered defect was filed.

## Readiness

Ready to merge and close issue #240.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-compat-2026-10-01.md
- docs/harness-acp-reverify-2026-10-01.md

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-240/.cache/final-validation.md
- kaola-workflow/archive/issue-240/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-240/finalization-summary.md
- kaola-workflow/archive/issue-240/mission-ledger.jsonl
- kaola-workflow/archive/issue-240/workflow-state.md
