# Finalization Summary — issue-191

## Delivered
Issue #191 (bug: stop --force sweeps a recorded agent_pgid without verifying process-group identity), accepted by Host on frozen candidate caf83eaa174f60fc8b5d52ffcbd96b1d1c049e89 (base d3d49c8, diff sha256 038e9e4a9ad446e2dc6fd378fa512c482b568eff8d66536085f913c5a55e65a6), plus doc-only docking commit 5d9877d (docs/api.md).
- Cause (code trace, scripts/kaola-acp.py at d3d49c8): force_kill_from_record (holder dead) and the reused-holder-PID branch of force_stop_unreachable SIGKILLed every live member of recorded_groups(), which trusted the recorded agent_pgid unconditionally for a record without agent_started and whenever the group's leader was gone. macOS reuses a pgid once its group empties, so a reused group could be killed. kaola-acp-sweep.py used the same resolution.
- Fix: recorded_groups(..., verified_only=True) for every signalling caller: the agent group counts only while its live leader (pid == pgid) has exactly the recorded agent_started second (no slack; cross-TZ exact). A pre-#132 record or a leaderless group proves nothing. unverified_agent_group() reports a recorded agent_pgid with live members that is not proven: never signalled, receipt `pgid_identity: "unverified"` + `pgid_identity_unverified` {code pgid-identity-unverified, agent_pgid, agent_started, live_members, signalled false}; retire_record() retires only this seat's record.json and never a newer record (also used by the reused-holder-PID branch). The validate sweep reports such groups under `pgid_identity_unverified` instead of signalling.
- Unchanged: normal exact-session stop through a live holder socket, holder/target attestation (expected instance id, argv anchor, answering socket), verified child-group sweeps, non-signalling status residue reporting.

Issue statement walk:
- "force stop verifies the group's identity before sweeping (recorded agent start time …)" → exact leader start-time match under verified_only; test_n3 (exact ±1 s rejected; cross-TZ probe [true, true]).
- "If the identity cannot be proven, it skips the sweep" → test_i191_force_stop_never_signals_an_unverified_agent_group (legacy record, other start time, leaderless group: force_killed_pids [], the group's own member still alive). Red on d3d49c8: the stand-in reused member was SIGKILLed.
- "clears the record only" → retired_record set, `status` → no-session; test_i191_reused_pid_stop_never_signals_an_unverified_agent_group (reused-holder-PID branch); test_i191_reused_pid_stop_never_retires_a_newer_record (red on d47254f7 candidate).
- "reports pgid-identity-unverified" → receipt fields asserted in both i191 tests.
- Legitimate owned group still stoppable → same i191 test final leg (recorded start time: swept, killed, residual_pids []); t7 dead-holder sweep; F2 reused-PID sweep (fixture now carries agent_started).

## Files Changed
scripts/kaola-acp.py, scripts/kaola-acp-sweep.py, skills/*/scripts/kaola-acp.py (10 generated, byte-equal to source), tests/contract/test-acp-contract.py, tests/contract/test-acp-sweep-contract.py, tests/contract/test-zcode-host-contract.py, CHANGELOG.md, docs/api.md.

## Test Coverage
New: test_i191_force_stop_never_signals_an_unverified_agent_group (end-to-end CLI, own `sleep` processes only; cleanup never signals a reaped group id), test_i191_reused_pid_stop_never_signals_an_unverified_agent_group and test_i191_reused_pid_stop_never_retires_a_newer_record (mocks, no signals). Extended: test_n3 verified_only exact/legacy asserts and cross-TZ probe. Adjusted to strict semantics: F2 fixture records agent_started; sweep contract asserts `pgid_identity_unverified == []` instead of listing an already-empty leaderless group; ZCode host contract accepts an adapter group that already exited (no live members) and asserts it is never unverified.

Acceptance legs:
- automated: `./scripts/render-skills.py --check` PASS; `./scripts/validate.sh` rc=0 foreground on clean tree at caf83ea (/tmp/kaola-191-validate-3.log) and again at 5d9877d after the doc commit (/tmp/kaola-191-validate-4.log); both end with sweep receipt residual_pids [], pgid_identity_unverified [], matched_pids []. Named prerequisite skips: 2 TestValidateWatchdog rows (bash 3.2.57 < 4, #151). Earlier run /tmp/kaola-191-validate.log (pre-review candidate) failed test-zcode-host-contract; fixed and superseded.
- focused: cross-TZ n3 under UTC, Asia/Shanghai, America/Los_Angeles, Australia/Lord_Howe OK; CHANGELOG/generated-copy tests (issue-162, 49, 130, 24) OK; docs/api.md readers (issue-147, 168, 52, 88) OK.
- review: independent code-reviewer pass on the first candidate (findings applied); Host review of d47254f7 (exact match, retire_record) applied; Host acceptance of caf83ea on 2026-09-27.
- unexecuted: live ACP smoke per platform — not run; transport and holder unchanged. No destructive live kill against unrelated processes; no stale record force-stopped.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- scripts/kaola-acp-sweep.py
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
- tests/contract/test-acp-contract.py
- tests/contract/test-acp-sweep-contract.py
- tests/contract/test-zcode-host-contract.py

## Documentation Docking
DOCKED — see .cache/doc-docking.md (docs/api.md fixed, CHANGELOG #191 Unreleased bullet; architecture/zcode-host/template/README no impact).

## Follow-Up Items
None filed. Not a defect for this run: retire_record names retired copies at one-second resolution (same pattern as the pre-existing pid-reused naming), so two retirements of the same seat within one second keep only the later copy; the live record handling is unaffected.

## Readiness
Ready: Host-accepted code candidate caf83ea + doc-only 5d9877d, validation recorded pass, docs DOCKED. Seats: restart not required (operator-diff: holder, bridge, quota catalog, adapters, platforms untouched). No release.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-191/.cache/doc-docking.md
- kaola-workflow/archive/issue-191/.cache/final-validation.md
- kaola-workflow/archive/issue-191/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-191/finalization-summary.md
- kaola-workflow/archive/issue-191/mission-ledger.jsonl
- kaola-workflow/archive/issue-191/workflow-state.md
