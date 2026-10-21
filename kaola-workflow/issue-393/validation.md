# Issue #393 focused validation

Run branch: `workflow/issue-393`
Candidate: `e4d5567b` (suite cleanup) on `d959ab2b` (coverage commit) on
`7b94ab81` (content-cycle unpin).

## Prerequisite: post-release content cycle

`main@be8a1ad9` is the v0.9.23 pin commit P. The pinned-stage `render-skills.py
--check` gate compares the tracked working tree with R `a56c3fa4` and rejects
any development change, so the standard post-release unpin is commit
`7b94ab81` (precedent: `f37a1b54`, `ea3297e7`). It changes only
`templates/grok-bot/accepted-revision.json` and the three generated
`hosts/grok-bot/` products. No KPR behavior changes.

## Suite

New file: `tests/contract/test-issue-393-cwd-carrier.py`.

Inventory row: `test-issue-393-cwd-carrier.py` in `scripts/validate.sh`
(`python_suites_all` and `python_suites_b`).

Related regression check on the same candidate:
`./scripts/validate.sh --suite test-issue-388-role-carrier.py` passed
(`test-issue-388-role-carrier.py` elapsed 10.848 s; total wall 11.7289 s;
`residual_pids: []`). That suite pins the existing role gate this route relies
on.

Standalone run:

```text
python3 tests/contract/test-issue-393-cwd-carrier.py
Ran 6 tests in 43.741s
OK
```

Inventory run from the run branch:

```text
./scripts/validate.sh --suite test-issue-393-cwd-carrier.py
validate: coverage: SUBSET RUN (1 of 146 suites selected; not full-inventory coverage)
...
test_worker_start_cwd_repair_self_prompt_is_compact ... ok
test_resume_preserved_worker_keeps_role_and_compacts ... ok
test_drain_restart_worker_keeps_role_and_compacts ... ok
test_direct_worker_holder_with_legacy_entry_compacts ... ok
test_direct_unknown_role_with_legacy_entry_compacts ... ok
test_direct_host_holder_still_gets_the_carrier ... ok
validate: elapsed test-issue-393-cwd-carrier.py                43.105 s
validate: total wall: 43.9712 s
residual_pids: []
```

The same run reported `render-skills: PASS`, all twelve
`validate-skill.*` rows PASS, and `kaola-grok-bot-verify: PASS` at the content
stage. The final standalone rerun at `e4d5567b` reported `Ran 6 tests in
43.153s` and `OK`. Earlier runs at the same test bytes reported `Ran 6 tests in
44.501s` (candidate `d959ab2b`, total wall 46.1919 s) and `Ran 6 tests in
44.088s` (pre-commit, total wall 45.5397 s). The suite selection is a subset run; the full inventory remains for the
Host.

## Renderer

```text
python3 scripts/render-skills.py --check
render-skills: PASS (11 workers + kaola-project-runner + kaola-delegator +
grok-bot host: 1 bridge skill, 2555 B, content stage, unpinned (not saveable);
budgets OK)
```

No template, worker Skill, orchestrator Skill or platform manifest changed, so
this run does not need `--write` beyond the standard content-cycle unpin.

## Pre-#388 control

The historical holder bytes from `f46e1d4e^` were run on the same direct-holder
route with a worker role and `--host-entry /kaola-project-runner`. The second
prompt began with `/kaola-project-runner`, contained `kaola-host-notify/1` and
`<<<heartbeat-prompt`, and contained the one-pass instruction. That is the only
variant that reproduced the reported prompt. The current holder on the same
argv produced `kaola-worker-notify/1`.

## Scope

This is a subset run. `KAOLA_FULL_GATE=1` is the Host's close-out gate. No
product code changed; the suite pins the current cwd-repair carrier route and
records the non-reproduction.
