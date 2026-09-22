VERDICT: ACCEPT_WITH_FINDINGS

Candidate: workflow/issue-132 @ 83052ce (base 428e7bb). Delta reviewed: `git diff 38056e7 83052ce -- ':!skills' ':!hosts'`.
I did not edit, stage or commit any tracked file. The only file I wrote is this handback. Scratch files are under /tmp/rv132g.

New finding counts: 0 high, 1 medium, 1 low, 2 informational.

## Status of the prior findings

| # | Status | Evidence |
|---|---|---|
| M1 | FIXED (reproduced) | /tmp/rv132g/m1.py. Host A was started under `/tmp/rv132g/rec` (holder 2306). The following steps ran under `/private/tmp/rv132g/rec`: (1) `list` returned `identity: verified`. (2) `start` of Host B was refused with `host-exists`, identity `verified`, and spawned nothing. (3) `stop --force --expected-holder-instance-id wrong` returned `holder-instance-mismatch` and wrote nothing. (4) `stop --force --expected-holder-instance-id <A>` returned `answering_socket: …/eefd7112….sock`, `stopped: true`, `residual_pids: []`, with no `holder_force_killed`. Afterwards the holder and agent were gone, and `/tmp` `status` read `stopped`. The new test `test_m1_other_spelling_of_the_root_reaches_the_live_holder` passes. |
| L1 | FIXED | `verified_hosts` adds `argv: "unreadable"` (scripts/kaola-acp.py:2453-2455). `host_exists_refusal` adds the unsandboxed-shell detail (:2476-2480). Both are asserted in `test_n6_*` of Issue132AnchorUnitTests. The refusal is still fail-closed. |
| L2 | FIXED | There is a comment at the spawn site (scripts/kaola-acp.py:2605-2606) and a comment on the regexes (:1004-1005). `test_t3` runs the real spawn argv through `holder_argv_anchor` (True) and `holder_argv_paths`, and checks that the socket equals the real one. |
| N3 | FIXED in the same-TZ case, with a regression (see M2) | `agent_started` is captured right after `Popen` from `process_table()` (scripts/kaola-acp-holder.py:743-745). `Popen` returns after exec, so this is the agent's own pid. The value is written by `Holder.write_record` (:1453). Measured: the recorded `agent_started` `'Tue Sep 22 13:00:08 2026'` equals `ps -o lstart=` under `LC_ALL=C`. The two parsers agree. The holder uses `split(None,4)` and the CLI uses `split(None,3)`, and each keeps the whole lstart remainder, including the double space that `%e` gives for single-digit days. The `libproc_ps` fallback (`%a %b %e %H:%M:%S %Y`, localtime) printed the same string as `ps` for a live group. /tmp/rv132g/n3.py cases: matching start gives the group included; another start gives excluded; a legacy record without `agent_started` gives included; leader killed with members remaining gives included. `ps` unreadable at spawn, or an agent that exits before the table read, leaves `agent_started` None, which takes the legacy trusted path. A zombie leader is filtered as `Z`, so the leader counts as absent and the group is included. The zombie still owns the pid, so this is safe. |

### The claim that a pgid cannot be reused while its group has members
This matches BSD/XNU pid allocation. The fork allocator skips a candidate pid that is a live pid, a live process-group id, or a live session id. So while any member holds group P, no new process can get pid P and lead a new group P. I did not test this empirically, because forcing pid reuse is impractical. A remaining TOCTOU exists between the `ps` snapshot and `killpg`: the group empties, the pid is reused, and the new process calls `setsid`. This is the same window that already existed, and the chance of hitting it is negligible.

## New findings

### M2 MEDIUM. Mechanism CONFIRMED end-to-end; trigger PLAUSIBLE (rare). A caller in another time zone no longer sweeps a dead holder's surviving agent, and the receipt claims `stopped: true, residual_pids: []`
- Code: scripts/kaola-acp.py:1265-1271 (`leader == (pgid, agent_started)`). The comparison is on `lstart` text, and that text is rendered in the process's local time zone. `PS_ENV` pins `LC_ALL=C` but not `TZ` (scripts/kaola-acp.py:1166, scripts/kaola-acp-holder.py:81). The `libproc_ps` fallback also uses `time.localtime`.
- Reproduction (/tmp/rv132g/tz.py). The mock agent was wrapped as `sh -c '<mock>; exec sleep 300'`, so the group leader outlives the holder's stdin EOF, as a wedged agent would. The Host was started with the default TZ, and then the holder got SIGKILL. `stop --force` under `TZ=UTC` returned `stopped: true, swept_pgids: [], force_killed_pids: [], residual_pids: []`, and the agent was still alive. `force_kill_from_record` then marks the record `state: stopped`. The control run with the same TZ returned `swept_pgids: [18922], force_killed_pids: [18922]`, and the agent was gone. At 38056e7 the agent group was trusted unconditionally and would have been swept.
- Consequences: residue cleanup regresses for the agent's main group. That affects `stop --force` and `kaola-acp-sweep.py`, which also calls `recorded_groups` (scripts/kaola-acp-sweep.py:133). The receipt gives a false "nothing left" fact. A retry cannot kill the agent either. `status` still reports `holder-lost` rather than outcome `stopped`, because it checks `pid_alive(agent_pid)` (:1098-1101), so a careful prove-gone step would notice.
- Trigger: the process that started the holder and the stopping or sweeping caller differ in `TZ`, for example a Host, launchd job or shell that has `TZ` set. The agent's leader must also survive the holder's death. The same TZ weakness already existed for child-group start comparisons. It is new for the agent's own group.
- Possible fix, left to the implementer: compare start epochs rather than text. Options are recording the libproc `start_tvsec`, or parsing both sides with the same TZ pinned. Pinning `TZ` in `PS_ENV` alone would break the spawn-record path, which calls `time.mktime` on a live `lstart`.

### L3 LOW. Mechanism CONFIRMED; trigger unrealistic. The argv-socket stop in `force_stop_unreachable` does not check the answering holder's instance before sending `stop`
- Code: scripts/kaola-acp.py:1426-1430. `answering_socket` returns any socket whose `state` reply has *a* `holder_instance_id`. The stop is sent without comparing that id with `record["holder_instance_id"]`. (`holder_identity` does compare them and reports `mismatch`.)
- Reproduction (/tmp/rv132g/foreign.py). Worker B was a live holder. A hand-written record for session C named a fake live process whose argv was `… kaola-acp-holder --record-dir <C dir> --socket <B's socket> --repo …`. `stop --force --expected-holder-instance-id <C id>` then went to B's socket, and B's holder refused with `holder-instance-mismatch`. The holder's `op_stop` check (scripts/kaola-acp-holder.py:3530-3533) and the socket peer check both apply, so this is safe. **Without** `--expected-holder-instance-id`, the same command returned `stopped: true` with `answering_socket` = B's socket, and B, a different session, was stopped.
- Trigger: C's recorded holder PID must be held by a process whose argv contains `kaola-acp-holder --record-dir <C's dir> --socket <another live holder's socket>`. That is not realistic. At 38056e7 the same setup would instead have SIGKILLed the fake process. The documented sweep always passes the expected id.
- Suggested fix: send the stop only when `state["holder_instance_id"] == record.get("holder_instance_id")`, or when `state["holder_pid"] == holder_pid`, and otherwise fall through to the refusal. This costs one line.

### I2 INFORMATIONAL. The other-spelling caller still sees `socket_ok: false` and `holder-socket-missing` on non-force ops
In the M1 reproduction, the `/private` `list` row showed `identity: verified` but `socket_ok: false`. `status` and a plain `stop` from that spelling still return `holder-socket-missing`, because only `holder_identity` and `stop --force` use the argv socket. The documented sweep (stop, then `--force` when that fails) now ends gracefully, so this is only a reporting inconsistency.

### I3 INFORMATIONAL. The identity probe can take up to twice as long
When the derived socket exists but is silent and the argv socket is also silent, `answering_socket` probes both. The `list` per-row bound therefore becomes 2 x 2 s, and the start guard's becomes 2 x 5 s. docs/api.md still says "bounded at 2 s per row" and "5 s".

## Brief question 3: any HIGH in 428e7bb..83052ce
None found. M2 is the most serious item. It is a regression in the new N3 identity check, not in the host-exists or root-holding logic, and it fails toward leaving a process rather than killing a foreign one.

## Commands run
- `git log --oneline -8`; `git diff --stat 38056e7 83052ce -- ':!skills' ':!hosts'`; `git diff 38056e7 83052ce -- ':!skills' ':!hosts' ':!tests'` and `-- tests`
- `sed`/`grep` reads of scripts/kaola-acp.py (op_or_holder_lost, recorded_groups, force_kill_from_record, force_stop_unreachable, holder-lost status, command stop params) and scripts/kaola-acp-holder.py (spawn, write_record, op_stop, process_table, libproc_ps), plus scripts/kaola-acp-sweep.py:120-140
- `env $U python3 /tmp/rv132g/m1.py <wt>/scripts/kaola-acp.py /tmp/rv132g/repo` (M1)
- `env $U python3 /tmp/rv132g/n3.py <wt>/scripts/kaola-acp.py` (N3 unit cases, libproc vs ps, TZ)
- `env $U python3 /tmp/rv132g/tz.py …`, run with `TZ=UTC` and with the same TZ as a control (M2)
- `env $U python3 /tmp/rv132g/foreign.py …` (L3)
- `env $U python3 tests/contract/test-acp-contract.py Issue132AnchorUnitTests Issue132HolderIdentityTests`: 15 tests OK
- `env $U python3 scripts/render-skills.py --check`: PASS
- Leak check with `pgrep -fl` for `rv132g`, `RVW-`, `sleep 300` and the fake sleeper: none remain. Every holder I started was stopped, and the M2 surviving agent group was `killpg`'d in `finally`. I did not run scripts/validate.sh.

(`$U` is the brief's `KAOLA_*` scrub, which excludes `KAOLA_VALIDATE_*`.)
