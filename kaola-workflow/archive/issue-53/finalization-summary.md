# Finalization Summary — Issue #53

project: issue-53
branch: workflow/issue-53
sink: merge
candidate: e60e87dd1d5c368ba6fdbe21c23e86b1ad353867 (frozen; worktree `.kw/worktrees/issue-53`, tree clean; 8 ahead / 0 behind origin/main ea287d6)
controlling-Agent acceptance: granted 2026-09-16 on e60e87d (full validate.sh, vendored vitest 133/133, dist byte-identical, independent merge-delta review PASS)

## Delivered

Issue #53 named four robustness edges from the #50 reviews. Each part and what satisfies it:

1. **Temp-file leftover** — `writePersisted` in `vendor/claude-code-acp/src/session-store.ts` hoists the temp path and `rmSync(temp, {force:true})` in the catch. Covered by vitest `leaves no temp sibling when the record cannot be renamed into place` (`tests/kaola-fork.test.ts`), red on baseline, green after.
2. **Stale cancel flag** — `prompt()` in `src/agent.ts` deletes `cancelledSessions[sessionId]` when a turn starts. Covered by harness `test_stale_cancel_does_not_taint_next_turn` (`tests/contract/test-issue-50-claude-acp-bridge.py`, fake-claude `fail` mode), red on baseline dist, green after rebuild; upstream `agent-cancel.test.ts` verbatim and green.
3. **Force-kill residue visibility** — holder (`scripts/kaola-acp-holder.py`) notes agent child process groups from the process tree (turn acceptance, stop entry) and from the bridge's synchronous spawn record (`KAOLA_ACP_CHILD_RECORD` → `children.jsonl`, `{pid,pgid,spawned_at,binary}`; stripped from the `claude` child env; compacted to live entries at agent start), records `agent_child_pgids`/`agent_child_groups`, sweeps them on stop (`swept_child_pgids`, covered by `residual_pids`); holder-lost `stop --force` (`scripts/kaola-acp.py`) sweeps recorded groups with the same identity checks (`swept_pgids`); `ps` start times read under `LC_ALL=C` with a one-sided [-1 s, +5 s] window. Covered by `test_force_stop_sweeps_detached_claude_groups` scenarios A–H in `tests/contract/test-issue-50-runner-integration.py` (healthy force, bridge SIGKILLed, holder+bridge SIGKILLed, both before first output, env-strip, zh_CN start, de_DE stop) plus `StoppedStatusTests` regression and vitest spawn-record tests (append when set, no append when unset).
4. **One-directional permit** — documented in `platforms/claude-code.yaml` `acp_quirks`, README.md, `docs/api.md`, vendor `UPSTREAM.md`: `permit` settles only the reported `tool_call` status because the `claude -p` child has no stdin and no `--permission-prompt-tool`. Prose evidence; the issue's own Measured section records the live 2.1.272 observation.

Reconciliation: origin/main ea287d6 (#52, #56) merged into 0c6f444 with `--no-ff` as e60e87d; only CHANGELOG.md conflicted (both appended under Unreleased), resolved keeping all three entries; mechanical three-way check and merge-delta review PASS.

## Files Changed

`git diff --stat origin/main e60e87d`: 40 files, +3453 / −309, all modifications, no deletions.

- Source: `scripts/kaola-acp-holder.py`, `scripts/kaola-acp.py`, `platforms/claude-code.yaml`
- Vendored fork: `vendor/claude-code-acp/src/{agent,claude-runner,session-store}.ts`, `tests/kaola-fork.test.ts`, `dist/index.js`, `dist/DERIVATION.json`, `UPSTREAM.md`
- Tests: `tests/contract/fake-claude.py`, `test-acp-contract.py`, `test-acp-follow-contract.py`, `test-issue-50-claude-acp-bridge.py`, `test-issue-50-runner-integration.py`
- Docs: `README.md`, `docs/api.md`, `CHANGELOG.md`
- Generated (rendered, never hand-edited): `skills/*/scripts/kaola-acp-holder.py`, `skills/*/scripts/kaola-acp.py` (8 workers), `skills/claude-code-kaola-project-runner/{SKILL.md,references/acp.md,scripts/platform.yaml,scripts/vendor/claude-code-acp/*}`

## Test Coverage

- vendored vitest: 133/133 (baseline 130; +1 session-store temp sibling, +2 spawn record)
- `test-issue-50-claude-acp-bridge.py`: 11/11, 212 checks (baseline 10/10, 206)
- `test-issue-50-runner-integration.py`: 7/7, 180 checks (baseline 6/6, 109)
- `test-acp-contract.py`: 45 OK (StoppedStatusTests regression added); `test-acp-follow-contract.py`: 12 OK (two-followers test samples the settled view)
- Reviewer custody experiments (Mission 8): un-pinning `PS_ENV` fails scenarios G/H; removing the env guard fails the vitest unset test.
- Unexecuted: live `stop --force` against a real `claude` child, and a live permit round trip (2.1.272 emits no `permission_request`); both are the documented UAT boundary carried over from #50, not claimed by this run.

## Validation

Acceptance legs at frozen e60e87d, worktree `.kw/worktrees/issue-53`:

- automated (finalization, 2026-09-16): `python3 scripts/render-skills.py --check` → PASS (budgets OK); `python3 vendor/claude-code-acp/kaola-dist.py --check` → OK rebuild=byte-identical; `env -u CLAUDE_ACP_CLAUDE_BIN npx vitest run` (in `vendor/claude-code-acp`) → 21 files, 133/133 passed; `./scripts/validate.sh` → `validate exit 0` (all unittest groups OK, generated Skill acceptance PASS, grok-bot verify PASS, test-issue-50 11/11 212 checks, runner-integration 7/7 180 checks incl. `test_force_stop_sweeps_detached_claude_groups` 70 checks, issue-51 6/6 117 checks, issue-52 9 OK, `git diff --check` clean; 15 leaked holder processes from test-acp-contract/watch temp record dirs terminated afterwards by exact pid, foreign sessions untouched) (log: session scratchpad `kaola-53-validate-final.log`, trailing `validate exit N`)
- automated (Mission 9, 2026-09-16): validate.sh run 8 `validate exit 0`, vitest 133/133, dist byte-identical, render PASS; reviewer's own validate.sh at e60e87d exit 0
- local review: `review-53` PASS on f315a4b, delta PASS on 3d478be, delta PASS on 0c6f444 (D1–D5 resolved), `review-53-merge` PASS on e60e87d (0 findings; observations: README.md:60 long line, follow-contract ResourceWarnings under Python 3.14, both pre-existing)
- manual/UAT: none required by the issue; controlling Agent independently re-ran validate.sh, vitest, dist check, and the merge-delta review and accepted e60e87d
- recorder: `kaola-workflow-validation-runner.js record --project issue-53 --verdict pass --command "python3 scripts/render-skills.py --check && python3 vendor/claude-code-acp/kaola-dist.py --check && (cd vendor/claude-code-acp && env -u CLAUDE_ACP_CLAUDE_BIN npx vitest run) && ./scripts/validate.sh"` → outcome recorded, `.cache/final-validation.md` verdict: pass, validated_candidate_hash cd60133feb5e383d97be93acb4f62d8e98afffe4dfa759119f1ae23aa3c79fc1 (hash binds the linked worktree; record resident in main's run folder)

## Changed Paths

Reported by `kaola-workflow-claim.js finalize --check --json` (36 paths, dirty_paths []):

platforms/claude-code.yaml; scripts/kaola-acp-holder.py; scripts/kaola-acp.py; skills/claude-code-kaola-project-runner/SKILL.md; skills/claude-code-kaola-project-runner/references/acp.md; skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py; skills/claude-code-kaola-project-runner/scripts/kaola-acp.py; skills/claude-code-kaola-project-runner/scripts/platform.yaml; skills/claude-code-kaola-project-runner/scripts/vendor/claude-code-acp/UPSTREAM.md; skills/claude-code-kaola-project-runner/scripts/vendor/claude-code-acp/dist/DERIVATION.json; skills/claude-code-kaola-project-runner/scripts/vendor/claude-code-acp/dist/index.js; skills/{codex,cursor-cli,devin,grok,kimi-cli,opencode,zcode}-kaola-project-runner/scripts/kaola-acp-holder.py; skills/{codex,cursor-cli,devin,grok,kimi-cli,opencode,zcode}-kaola-project-runner/scripts/kaola-acp.py; tests/contract/fake-claude.py; tests/contract/test-acp-contract.py; tests/contract/test-acp-follow-contract.py; tests/contract/test-issue-50-claude-acp-bridge.py; tests/contract/test-issue-50-runner-integration.py; vendor/claude-code-acp/UPSTREAM.md; vendor/claude-code-acp/dist/DERIVATION.json; vendor/claude-code-acp/dist/index.js; vendor/claude-code-acp/src/agent.ts; vendor/claude-code-acp/src/claude-runner.ts; vendor/claude-code-acp/src/session-store.ts; vendor/claude-code-acp/tests/kaola-fork.test.ts

(The check omits README.md, docs/api.md, CHANGELOG.md, which `git diff --stat origin/main e60e87d` also lists; they are documentation-only.)

## Documentation Docking

`.cache/doc-docking.md` → DOCKED. README, docs/api.md, CHANGELOG, platform manifest, vendor UPSTREAM.md updated in the candidate; generated Skills and dist regenerated and checked; architecture/conventions/decisions and dated evidence docs judged no-impact.

## Follow-Up Items

No new issue filed. Observations carried as documented boundaries, none a defect this run measured as user-visible:

- F2 residual: a same-group grandchild that outlives a never-noted `claude -p` (bridge died before spawn-record append could not happen since the append is synchronous; the residual is a grandchild forked by `claude` itself into the same group after the sweep) — documented boundary in docs/api.md.
- F5: a silent `ps` failure yields an empty sweep (pre-existing pattern shared with `residual_pids`).
- `scripts/kaola-pane-relay.py` hashes a raw `lstart` (pre-existing, PTY path, outside #53 scope).
- C2 nit: `spawn_record_dir` recomputes a directory `op_or_holder_lost` already holds; README.md:60 long line; follow-contract ResourceWarnings under Python 3.14.
- Per-run leak of holder/mock-agent processes from `test-acp-contract.py`/`test-acp-watch-contract.py` temp record dirs (15–30 per validate.sh run, pre-existing in every tree); terminated by exact pid after each run.
- Release v0.3.2 is user-authorized after all issues close and is not performed by this finalization.

## Closure Decision

Issue set: #53 only. All four members satisfied; close on sink (`issue_action: close`). No keep-open.

## Readiness

READY_FOR_FINALIZE — pending the finalize transaction, merge sink, and closure audit recorded below.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-53/.cache/doc-docking.md
- kaola-workflow/archive/issue-53/.cache/final-validation.md
- kaola-workflow/archive/issue-53/.cache/mirror-digest.json
- kaola-workflow/archive/issue-53/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-53/finalization-summary.md
- kaola-workflow/archive/issue-53/mission-list.md
- kaola-workflow/archive/issue-53/workflow-state.md
