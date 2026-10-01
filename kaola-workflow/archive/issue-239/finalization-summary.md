# Issue 239 — Scope Agent prompts by role

## Delivered

Routine Delegator, Host, task-worker, and platform-runner prompts now carry the text that role owns. Inquiry commands live in the Delegator snapshot; start, resume, replace, and attach stay in handoff. The Host entry keeps identity, canonical cwd, no blind replay, accept-before-finalize, the directory rule, and the no-login line. Confirmed limit and account refusal stay on the short #207/#216 rule. The quota API exposition and package JSON examples moved to `docs/api.md`.

No release, tag, install, or CHANGELOG release section. Budgets were not raised. `templates/grok-golden/` and the Grok Bot bridge were not edited.

## Candidate

9b4012bc9d87a71dd8114d6fa2945372cdf2e30c, workflow/issue-239.
Worktree: /Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-239
Baseline: d2b03772. Diff: 56 files, +503/−912.

## Evidence and acceptance

Host ACCEPTANCE: PASS. The Host judged that diff against the issue per-surface table and the agreed design in `/tmp/kpr-progressive-disclosure-review.md` (A1–A14, the short seat-failure rule, the three load-cost classes, and the corrected startup rows).

Host independent checks on this tree, all matching the worker report:
- operator set (`scripts/kaola-acp-holder.py`, `scripts/kaola-zcode-acp.py`, `scripts/kaola-quota.py`, `scripts/adapters`, `platforms`) has zero diff. Seats: restart not required.
- `templates/budgets.json`, `templates/grok-golden/`, and `hosts/grok-bot/` untouched.
- Generated UTF-8 bytes: Host entry 16148, Delegator entry 4094, wake 8104, skeleton 7866, worker-profiles 8042, quota-packages 3222.
- `docs/api.md` is the specified relocation of the quota API exposition.
- Invariants checked inline: no-login, identity, canonical cwd, no blind replay, accept-before-finalize, directory-rule roster with the transport line, `sweep=` retained, #207/#216 short rule including the skeleton revoked-Elite-stays-revoked form, and host-brick confirmed-limit-only fallback.
- `./scripts/render-skills.py --check` PASS, progressive-disclosure OK, validate-skill PASS on the Host rerun. These are focused checks. This record has no complete `./scripts/validate.sh` receipt, so it does not call that suite green.

Worker evidence reused for the same bytes: `./scripts/render-skills.py --check`; `python3 tests/contract/test-progressive-disclosure.py` (15 OK); `python3 scripts/validate-skill.py` (`validate-skill: PASS (12 Skill(s))`); contract tests 41, 49, 52, 65, 68, 70, 72, 74, 75, 94, 118, 148, 168, 218; `test-generated-skills.py` PASS; `test-lifecycle-contract.py` PASS; `test_canonical_heartbeat_spec_stays_one_set` 12 checks OK. Same limit: focused checks, not a complete `./scripts/validate.sh` receipt.

Equivalent required-read file bytes, generated UTF-8, baseline `d2b03772` to candidate `9b4012bc`: main Skill plus `quota-packages.md` is 25523 -> 19370. The 33715 baseline figure is that pair plus `worker-profiles.md` (8192). That profiles file is a conditional extra read when those rules are not already in context, not an inevitable cost of the main-plus-quota path. These figures are file bytes. They are not a token count or a cache measurement.

`.cache/final-validation.md` in this run folder binds the recorded verdict to this worktree.

Protected files, including untracked `docs/harness-acp-compat-2026-10-01.md` and `docs/harness-acp-reverify-2026-10-01.md`, were not staged or deleted.

## Known failures or unverified scope

`tests/contract/test-issue-187-delegator-any-host.py` `NonZCodeHostLifecycle` failed 3 tests with `holder-start-timeout` on this candidate. The Host reran the same file on unmodified baseline `d2b03772` and got the same 3 failures. The retained baseline transcript is `/tmp/187-baseline.log` (`FAILED (failures=3)`; the same three tests, each `holder-start-timeout`). A separate candidate transcript file was not retained next to that log; the identical outcome is the Host's recorded rerun of that file on `d2b03772` against the candidate. Identical outputs prove the failures are pre-existing. The root cause is unknown. Those outputs do not prove an environmental cause. The wording class `GeneratedDelegator` in that file passed on the candidate. No live failure injection was added. The rest of `test-zcode-heartbeat-contract.py` is holder delivery; holder sources have zero diff, and only `test_canonical_heartbeat_spec_stays_one_set` was rerun.

No release, tag, install, or CHANGELOG release section, by the Host boundary for this run. `main-skill-build.json` hashes changed; this run did not reinstall.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

The `green: true` mark binds the focused command in `.cache/final-validation.md` (`render-skills.py --check`, `test-progressive-disclosure.py`, and `validate-skill.py`). It is not a `./scripts/validate.sh` receipt.

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- docs/api.md
- scripts/render-skills.py
- skills/claude-code-kaola-project-runner/SKILL.md
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/SKILL.md
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/SKILL.md
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/SKILL.md
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/SKILL.md
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/SKILL.md
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/SKILL.md
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-delegator/SKILL.md
- skills/kaola-delegator/references/host-brick.md
- skills/kaola-delegator/references/host-platforms.md
- skills/kaola-delegator/references/snapshot.md
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/doc-maintenance.md
- skills/kaola-project-runner/references/heartbeat-skeleton.md
- skills/kaola-project-runner/references/host-entry-matrix.md
- skills/kaola-project-runner/references/host-startup.md
- skills/kaola-project-runner/references/qa-evidence.md
- skills/kaola-project-runner/references/quota-packages.md
- skills/kaola-project-runner/references/worker-profiles.md
- skills/kaola-project-runner/references/workflow-worktree.md
- skills/kaola-project-runner/references/zcode-host-dispatch.md
- skills/kaola-project-runner/references/zcode-native-skill-entry.md
- skills/kimi-cli-kaola-project-runner/SKILL.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/SKILL.md
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/SKILL.md
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/SKILL.md.tmpl
- templates/kaola-delegator/SKILL.md.tmpl
- templates/kaola-delegator/references/host-brick.md
- templates/kaola-delegator/references/host-platforms.md.tmpl
- templates/kaola-delegator/references/snapshot.md
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/doc-maintenance.md
- templates/orchestrator/references/heartbeat-skeleton.txt
- templates/orchestrator/references/host-entry-matrix.md
- templates/orchestrator/references/host-startup.md.tmpl
- templates/orchestrator/references/qa-evidence.md
- templates/orchestrator/references/quota-packages.md
- templates/orchestrator/references/worker-profiles.md.tmpl
- templates/orchestrator/references/workflow-worktree.md
- templates/orchestrator/references/zcode-host-dispatch.md.tmpl
- templates/orchestrator/references/zcode-native-skill-entry.md
- tests/contract/test-issue-148-quota-packages.py
- tests/contract/test-issue-41-orchestrator.py
- tests/contract/test-issue-74-kaola-delegator.py

## Follow-Up Items

None filed as a defect of this delivery. The three test-187 failures are a pre-existing observation. Their cause stays unknown.

## Readiness

Ready to merge and close issue #239.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-compat-2026-10-01.md
- docs/harness-acp-reverify-2026-10-01.md

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-239/.cache/final-validation.md
- kaola-workflow/archive/issue-239/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-239/finalization-summary.md
- kaola-workflow/archive/issue-239/mission-ledger.jsonl
- kaola-workflow/archive/issue-239/workflow-state.md
