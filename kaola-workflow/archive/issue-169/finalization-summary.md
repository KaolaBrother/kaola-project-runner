# Finalization Summary — issue-169

Issue: #169 — `command_start` repeats the host-capable and host-exists checks
`pre_spawn_refusal` already made.
Branch: `workflow/issue-169` (base `2e18946`, candidate `fe480d3`).
Sink: merge.

## Delivered

Removed the two unreachable guard blocks from `command_start` in
`scripts/kaola-acp.py`:

- the Issue #122 block (`host_capable` / `host_session` →
  `host_entry_unsupported`), and
- the Issue #132 block (`host_session` → `verified_hosts` → `host_exists_refusal`).

Since #164, `command_start` calls `pre_spawn_refusal(args, repo)` first on the same
`args` in the same process and returns on refusal, and `pre_spawn_refusal` runs both
guards first (`scripts/kaola-acp.py:3252-3259`). Nothing is written or spawned in
between, so the duplicated blocks could never fire. Each guard now lives exactly once.
The two comment blocks are replaced by a single 2-line note naming what already returned.

Pure dead-code removal: no behavior change. `pre_spawn_refusal` logic, the bridge and
runtime checks, the holder, adapters, and `platforms/` were not touched.

## Files Changed

12 paths, +35/−165:

- `scripts/kaola-acp.py` (+2/−15, one hunk)
- `skills/*/scripts/kaola-acp.py` × 10 (re-rendered, byte-identical to source)
- `CHANGELOG.md` (+13)

No frozen surface (`templates/grok-golden/`, `hosts/`), no adapter, holder, bridge, or
`platforms/` file changed. The operator test
`git diff 2e18946 fe480d3 -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/adapters platforms`
is empty, so `Seats: restart not required` is accurate.

## Test Coverage

Existing coverage already proves the refusal path; no new test was required (the issue
states this explicitly when a focused assertion already proves `command_start` refuses
via `pre_spawn_refusal`).

- `tests/contract/test-issue-119-host-entry.py` — 11/11 tests, 160 checks, including
  `test_issue_122_entryless_host_fails_closed` (29 checks). Its "T1 Host start" asserts
  a Host-named entry-less start refuses `host-entry-unsupported` through the real CLI.
- `tests/contract/test-issue-74-kaola-delegator.py` — 186 assertions, 0 failed,
  including `test_one_host_per_repo_refuses_host_exists` (T1/T5/T13).
- Adjacent host suites green: `test-zcode-host-contract.py` (3/3),
  `test-issue-49-grok-bot-host.py` (45 tests OK).
- `./scripts/render-skills.py --check` — PASS; 10/10 rendered copies byte-identical
  (`cmp`) to the source.

### Flake note (known, pre-existing)

The finalize-time `./scripts/validate.sh` exited 1 with 46 OK / 2 FAILED; **both**
reported lines are the same known load-sensitive flake in
`tests/contract/test-issue-98-dsh-acp.py`
(`test_a_confined_boot_write_failure_names_its_cause`: got `acp-initialize-timeout`,
expected `acp-initialize-failed`; the watchdog's `FAILED: test-issue-98-dsh-acp.py`
summary line is the same suite).

- Focused re-run on the candidate: **passes** — the full 37-test suite reaches OK
  (reproduced; needs a quiet machine).
- Unmodified base `2e18946` reproduces the same failure, including in isolation
  (1 OK / 4 FAILED across 5 isolated runs).
- The failing test exercises the macOS seatbelt-confined boot-write path and is
  unrelated to `command_start`'s refusal guards.

Recorded verdict: `pass` (`.cache/final-validation.md`), validated against candidate
tree hash `b7488536fe16760b2a53afbb654ba71ddf77369b89e88fc4ffe3d02289ead90c`.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py

## Documentation Docking

`.cache/doc-docking.md` — **DOCKED**. `CHANGELOG.md` already carries the #169 entry with
the required `Seats: restart not required` line. `docs/api.md` and `docs/zcode-host.md`
describe the refusal *behavior* (unchanged; both refusals still fire from
`pre_spawn_refusal`) and name no removed code, so no doc update was needed. `docs/api.md`
drift-list updates are a separate follow-up issue, outside this run.

## Follow-Up Items

- None filed by this run. The review's non-blocking observations (a two-line rationale
  comment on the guards in `pre_spawn_refusal`, and removing the residual #132 timing
  window) were assessed as optional and were not converted into work for #169; changing
  the frozen candidate would invalidate the accepted PASS.
- Separate, already-authorized follow-up (not this run): `docs/api.md` drift-list updates.

## Readiness

Acceptance: Claude Code review `VERDICT: PASS for issue #169`, no blocking findings
(receipt `/tmp/kpr-i169-review2-receipt.json`). Candidate frozen at `fe480d3`, tree clean.
Ready to archive, sink-merge to main, and close #169.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-169/.cache/doc-docking.md
- kaola-workflow/archive/issue-169/.cache/final-validation.md
- kaola-workflow/archive/issue-169/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-169/finalization-summary.md
- kaola-workflow/archive/issue-169/mission-ledger.jsonl
- kaola-workflow/archive/issue-169/workflow-state.md
