# Finalization Summary — issue-354

## Delivered

Issue #354 (bookkeeping 1A): state-bloat diagnosis, and a settled row must leave.

- `state check` adds a computed `state-bloat` diagnosis. It is not stored and it does not accumulate. It lists an accepted-done task, a cancelled task, a settled decision, an alert whose `inputs` is empty, and a shell task whose evidence is only `retired:tasks/ID` with empty duty fields. Each item names the collection, id, revision, and a `state retire` command.
- A row over 1536 bytes is a hint, not a gate. There is no field length cap, no truncation, and no `field-too-long`.
- `done-not-retired` stays watch until `maintenance.handled_host_revision` covers that task's `host_revision`, then warn. The warn does not refuse a later write.
- `carrier-unproven` names `state migrate --live`.
- The copied i338 shape (unknown, `fingerprint-differs`, collected outcome absent, status `no-session`, live session absent) retires on the stale-collect session-gone route and writes no index bytes. A collected outcome of `stopped` stays on the continuation route. A row with no collected proof stays on the dead-holder route.
- `state migrate` still does not delete a done task, and it still does not write a hash-named backup.
- Rebased onto `c9af2517` after #353. `scripts/kaola-dispatch.py` auto-merged; the sweep changes stay. `CHANGELOG.md` keeps both Unreleased bullets. Generated `main-skill-build.json` hashes were regenerated with `./scripts/render-skills.py --write`.

## Candidate

Branch `workflow/issue-354`, parent `c9af2517`.

- `b3cefc0ceeaf262989ebe2da6e89d44d88edd33a` — `Diagnose state bloat and retire a settled row (#354)`

Acceptance candidate: `b3cefc0c`. Worktree clean. This finalize adds no implementation commit.

Host acceptance: ACCEPTED.

The operator diff of this change against its parent is empty (`scripts/kaola-acp-holder.py`, `scripts/kaola-zcode-acp.py`, `scripts/kaola-quota.py`, `scripts/kaola-record-contract.py`, `scripts/adapters`, `platforms`, `scripts/kaola-acp-paths.py`). For this change, seats do not need a restart. The `## Unreleased` section line stays `Seats: restart required` because #353 changes the holder.

## Evidence

- Fail-on-main: the final suite against unmodified `b35165ff` `scripts/kaola-dispatch.py` was `Ran 12 tests in 3.729s`, `FAILED (failures=7, errors=2)`. After the change, `./scripts/validate.sh --suite test-issue-354-state-bloat.py` is `Ran 12 tests` / `OK`.
- Focused suites on `b3cefc0c` (`KAOLA_LAUNCH_BACKEND=direct`, proxies and `KAOLA_ZCODE_*` / `KAOLA_ACP_DISPATCHER` cleared): 354 `Ran 12 tests in 10.281s` OK; 255 `Ran 142 tests in 98.406s` OK; 259 `Ran 63 tests in 39.849s` OK; 286 `Ran 29 tests in 7.718s` OK; 348 `Ran 27 tests in 35.205s` OK.
- Host full inventory `./scripts/validate.sh` (no `--suite`) in the worktree at `b3cefc0c`, direct backend, clean environment: exit 0, 1339.38 s, no flake. Recorded in `.cache/final-validation.md`.
- `./scripts/render-skills.py --write` and `--check` PASS (content stage, unpinned, 2555 B).
- Evidence comments: issuecomment-6259667299, issuecomment-6260432909.

## Known failures and unverified scope

- No known product failure on `b3cefc0c`.
- No release, tag, or install in this finalize.
- The implementation choices named in issuecomment-6259667299 (hint threshold 1536, warn that does not refuse writes, structural shell, empty `inputs` as a resolved alert, 1A-4 only on this diagnosis, no auto-retire, the stale-collect shape only, bridge left at the content stage) stand as accepted with this candidate.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- scripts/kaola-dispatch.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/lifecycle-state.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/references/lifecycle-state.md
- tests/contract/fixtures/issue-354/i338-effort-max.json
- tests/contract/fixtures/issue-354/i338-task.json
- tests/contract/test-issue-354-state-bloat.py

## Follow-Up Items

- None filed.
- No release, tag, or install in this finalize.

## Readiness

Host accepted `b3cefc0c`. The Host full-gate result is reused. Merge sink into local main after #353, push to origin, close issue #354, release the claim label, archive.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-354/.cache/final-validation.md
- kaola-workflow/archive/issue-354/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-354/finalization-summary.md
- kaola-workflow/archive/issue-354/mission-ledger.jsonl
- kaola-workflow/archive/issue-354/workflow-state.md
