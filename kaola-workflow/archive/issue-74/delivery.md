# Issue #74 delivery

Current candidate: `eb9585208d40da0c9f21add3596278833b0ba3bb` on `workflow/issue-74`.
Previous freeze `536c6bd19c309bcf51d0224a1206926fd7b18639` is superseded (not ACCEPT).
Docs freeze for other workers: `380ca2b25fef708bf038dc8fb010c146718dcf95`.
Base: origin/main `513e8e1f82172fce3145c893c6db3072759ea457` (#82 sink; includes #69 and #83).
OUTER ACCEPT received for this exact SHA. Finalize/archive/sink/close in progress.
No product mutation after ACCEPT. Grok Bot account UAT remains unexecuted, not claimed.

Display name **Kaola-Delegator**, skill id/dir **kaola-delegator**.

## This freeze vs 8b6c20f

Safely rebased onto origin/main after #79 published and #80 sunk. Kaola-Delegator
is preserved (no handoff pointer; live Host from canonical repo + standard
Runner name/`status`; new Host only after current authorization is complete).
The #79 ZCode 3.12.3 adapter is preserved byte-identical to origin/main.

`44a17b9` is an equal-length issue-49 host-template probe: the Delegator bridge
is 2536 B / 2560, so the old append sentence overflowed `bridge_bytes`. No
budget was raised.

`942c4c8` adds the first-beat check the outer review asked for: after the first
Host `end_turn`, compare the Project Plan and authorization with Host
file-read/work-product evidence and the first worker dispatch receipt. Do not
trust Host self-description. Mismatch: correct; do not accept completion. No
new script, gate, ledger, or budget. Live A→B was not re-run (guidance only).

## Real A→B (this freeze)

Previously missing real path is now measured on an isolated scratch Git repo
with the candidate adapter: `kaola-workflow/issue-74/evidence/live-ab-44a17b9/`.
A found no Host, started one standard Host after explicit test authorization,
the Host loaded Project Runner and dispatched one Devin SWE-2 Max worker, ended
the turn, event wake reported the worker result (`RECEIPT.txt` =
`KAOLA74-AB-TOKEN`), B attached the same live Host (same holder and
`acp_session_id`, no second start) and followed up, then exact stop with
`residual_pids=[]`. Foreign sessions unchanged. See `RESULTS.md` in that
folder. Fake ACP tests are not that path.

## Still documentation-only / untested

- Missing-authorization non-start (Skill/README/handoff: do not `start` a blank
  Host). This live run **had** authorization.
- Grok Bot live UAT.
- Stopped-Host `--resume sess_*` restoring the same native session (still the
  3.12.3 cannot-resume measurement; latest comments allow a new Host after
  confirmed stop).

## Targeted corrections vs 4c76a15 (this freeze)

1. After exact Host `stop`, try attested native `--resume` first. Native
   resume is backend-dependent; do not assume `session/close` always spends
   `sess_*`. A new Host is allowed only after proven failure and complete
   authorization. Issue #84 is not merged here.
2. Fixture `ORIGINAL_TASK` uses `quota_account=1 job` and
   `quota_token=10000 tokens` plus an explicit `delivery_stop_boundary`.
   Those are figures, not an account name or a task count.
3. Afterward again states the outer Agent is not automatically awakened by
   inner Host activity.

Evidence: `kaola-workflow/issue-74/evidence/validate-resume-wording/`.
`render --check` PASS; grok-bot-verify PASS; `git diff --check` PASS; full
`validate.sh` **exit 0** (148 issue-74 assertions). Fake tests stay labeled
fake; missing-auth stays untested. No #81/#84 adapter edits.

## Outer-review fixes vs 337f805 (this freeze)

1. Host `stop` carries `holder_instance_id` from the existing start/`status`
   receipt as `--expected-holder-instance-id`. `holder-instance-mismatch` is
   refused; re-read `status`. Live attach compares holder, not repo+session
   name alone.
2. Fake ACP test is `test_fake_acp_host_worker_event_and_live_status` and
   cites `evidence/live-ab-44a17b9/`; it is not outer Delegator A→B.
3. New Host start happens only after authorization is on disk. Missing-auth
   non-start is `test_missing_authorization_non_start_is_documentation_only`
   (`measured: false`, `coverage: untested`).
4. After a full Codex/generic install, a filtered `--platform` reinstall
   updates an already-installed Delegator and a filtered uninstall removes it.

Evidence: `kaola-workflow/issue-74/evidence/validate-holder-fix/`.
`render --check` PASS; grok-bot-verify PASS; `git diff --check` PASS; full
`validate.sh` **exit 0** (140 issue-74 assertions). Live A→B not re-run.
#83 lane semantics kept. No budget raise.

## Rebase onto sunk #83 (this freeze)

Waited for GitHub #83 remotely CLOSED, then rebased `942c4c8` onto origin/main
`94d6792`. Kept both validate suites and docs: #83 `run_suite_lane` continues
after FAILED and reports SKIPPED for missing logs;
`test-issue-83-lane-failure-visibility.py` stays in lane A;
`test-issue-74-kaola-delegator.py` stays in lane B. CHANGELOG carries both
#74 and #83 Unreleased bullets. Adapter still matches origin/main.

On this worktree: `render --check` PASS, grok-bot-verify PASS,
`git diff --check` PASS, full `./scripts/validate.sh` **exit 0**. Evidence
`kaola-workflow/issue-74/evidence/validate-rebase-94d6792/` (`SUMMARY.txt`,
`validate.sh.log`, `candidate.diff`). Live A→B was not re-run.

## Renderer / contract

- `render-skills.py --check` PASS
- `kaola-grok-bot-verify.py` PASS (2536 B content-stage unpinned)
- `test-issue-74-kaola-delegator.py` 108 assertions PASS
- `test-issue-79-zcode-312.py` 19/19 PASS
- `test-zcode-acp-contract.py` 34/34 PASS
- `test-issue-49-grok-bot-host.py` 43/43 PASS after `44a17b9` (Errno 66 gone via
  #80 fixture knobs kept through the rebase)

Full `validate.sh` is not re-claimed green in this delivery. Targeted contract
logs: `evidence/validate-02f37b0/`.

Grok Bot co-location remains: account-bridge path attests Host ops with
`--project --worker zcode --session`; Codex/generic skip. Locator subprocess
receipts in `evidence/grok-bot-colocation/` are not a Grok Bot Agent.

Waiting outer ACCEPT. Do not finalize, archive, sink, merge, or push.
