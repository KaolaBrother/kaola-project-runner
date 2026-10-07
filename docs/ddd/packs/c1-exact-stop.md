---
pack_schema: kaola-ddd-pack/1
id: c1-exact-stop
status: current
owner: host
context_primary: session-runtime/C1-lifecycle
contexts_touched: session-runtime/CORE-identity, session-runtime/C3-events, orchestration-state/C6-recovery, orchestration-state/C4-state
baseline_commit: 4c30b71d0b964628c5a39159ff0cd89504adcd6b
related_issues: 283, 73, 132, 191, 255, 280, 281, 289
---

# Second pack — exact-stop a seat (C1 lifecycle, crossing CORE identity, C3 events, C6 recovery and C4 state)

Work unit: `kaola-acp.py <platform> stop --repo R --session S [--expected-holder-instance-id H]
[--force] [--preserve-dispatched-workers]` ends one owned ACP session. "Exact" means the stop is
bound to the holder instance the Agent verified, so a same-named session rebuilt by a later holder
is refused instead of stopped (`A:6185-6187`; Host guidance
`templates/orchestrator/references/workflow-worktree.md:34-38`). The proof that the seat is gone is
the stop receipt plus a later `status`, not the completed call
(`templates/SKILL.md.tmpl:131-133`).

The unit crosses five boundaries:

- **C1 lifecycle**, where the stop runs: the Runner CLI decides the path, the holder runs the
  cooperative shutdown;
- **CORE identity**, which decides *which* processes are this seat's: record directory, socket
  path, `holder_instance_id`, holder argv anchor, and process-group identity by start time;
- **C3 events**, where a refused stop leaves its only trace;
- **C6 recovery**, because a Host carrier's stop also ends its own Sideagent node;
- **C4 state**, read-only: `state retire` consumes the stop proof (the pilot's G9).

All citations are at `4c30b71d`. `git diff --stat 8b3779c9 4c30b71d -- scripts tests templates
platforms` is empty, so the pilot pack's citations into the same files still hold. `A` means
`scripts/kaola-acp.py` and `H` means `scripts/kaola-acp-holder.py`. Gap ids here are `S1`–`S3`,
so they do not collide with the pilot's `G1`–`G9`.

## Vocabulary

| Term | Meaning in this unit | Defined at |
|---|---|---|
| seat / session | One Runner session, addressed by platform + `--session` + canonical repo. Its record directory is `<record_root>/<platform>/<session>/<sha256(repo)[:16]>`. | `A:804-816` |
| holder | The `kaola-acp-holder.py` process that owns one session's agent and socket | `H:5532`, `A:1754` |
| `holder_instance_id` | The holder's per-process identity. A restart under the same name gets a new one. This is what makes a stop "exact". | `H:2002`, `A:6185-6190` |
| exact stop | A stop with `--expected-holder-instance-id`. A live holder refuses a mismatch before it changes anything. Without the flag the stop keeps the old unbound behaviour. | `H:5536-5539`, `A:2300-2306` |
| `stop --force` | Skip the cooperative cancel/close and terminate at once. With a live but silent holder, also the only path that signals the holder itself. | `H:5555`, `H:5561`, `A:1884-1885`, `A:1900-1901` |
| cooperative stop | The holder's non-force path: `session/cancel` an active turn (`CANCEL_GRACE` 5 s), `session/close` if the agent advertises it, close stdin, wait `EXIT_GRACE` 5 s | `H:5561-5582`, `H:43`, `H:47` |
| group sweep | SIGTERM the agent's process group, `TERM_GRACE` 3 s, SIGKILL; then the same for out-of-group child groups whose recorded member identity still holds | `H:5627-5692`, `H:48` |
| `stopped` (receipt key) | Path-dependent. The holder and the dead-holder sweep set `stopped: true` unconditionally, next to whatever `residual_pids` they measured. The reused-pid path sets `stopped: not leftover`. So it is **not** "nothing is left" in general; `residual_pids` and `status` are. | `H:5587-5596`, `A:2248-2258`, `A:2347` |
| `stopped` (record `state`) | The C1 holder state value written at the end of a stop. C4 reads it verbatim (pilot). | `A:841-843`, `H:5587-5588`, `A:2277-2286` |
| `residual_pids` | Live pids still in the swept groups after the stop. `[]` is the evidence of a clean stop. | `H:5688-5692`, `A:2244-2247` |
| `holder_lost` | The holder process is already dead. A stop then sweeps from the record (`force_kill_from_record`). For `status`, a dead holder with record `state: stopped` and no residual reads `outcome: stopped` instead. | `A:1874-1876`, `A:1825-1866` |
| `pid_reused` | The recorded holder pid is alive but its argv is provably another process: it gets no signal, and the record is retired | `A:2317-2356` |
| `pgid-identity-unverified` | The recorded agent pgid has live members but no live leader with the recorded start time: never signalled | `A:2177-2191` |
| retire (C1 meaning) | `retire_record`: rename `record.json` aside to `record.<reason>-<ts>.json`, so `status` then reads `no-session`. Same word as C4's `state retire`, different act (pilot vocabulary, map). | `A:2194-2203` |
| preserve | `--preserve-dispatched-workers`: a Host stop keeps the process trees of workers it dispatched. A Sideagent's stop always does. Needs holder feature `preserve-dispatched/1`. | `A:2206-2227`, `A:1908`, `H:248`, `H:5659-5668`, `H:258` |
| node reclaim | A Host carrier's own Sideagent node is not a dispatched worker: it ends with the carrier in every stop mode | `H:3958-3980`, `H:5560` |

## Inputs and outputs

| Direction | Artifact | Schema / version | Owner of the format |
|---|---|---|---|
| in | `stop --repo --session [--expected-holder-instance-id --force --preserve-dispatched-workers]` | argparse `A:5895-5901` | C1 |
| in | `record.json` in the record directory | no schema field; key set written by `H:1995-2035` (`holder_features` advertises `preserve-dispatched/1`, `H:2024`, `H:248`) | C1 (holder) |
| in | `children.jsonl` spawn record | one JSON object per line: `pid`, `pgid`, `spawned_at` | CORE identity (`A:1995-2006`) |
| in | process table | `ps -o pid,pgid,state,lstart` under `LC_ALL=C` | OS, read by CORE identity (`A:2009-2017`, `A:1910`) |
| in/out | holder socket op `stop` | newline JSON `{"op":"stop","params":{force, expected_holder_instance_id?, preserve_dispatched_workers?, require_idle?}}` | C1 (`H:5832-5833`) |
| out | stop receipt (stdout JSON) | live holder: `stopped`, `residual_pids`, `swept_child_pgids`, `spared_child_pgids`?, `agent_exit_code`, `agent_exit_signal`, `mutation_status` (`H:5589-5596`). Dead holder: `stopped`, `holder_lost`, `swept_pgids`, `force_killed_pids`, `residual_pids`, `mutation_status`, `pgid_identity`? (`A:2248-2258`). Reused pid: `stopped` (= no leftover), `pid_reused`, `holder_signalled: false`, `retired_record` (`A:2346-2355`). | C1 |
| out | refusals | `error.code` `holder-instance-mismatch` (`H:4635-4650`, `A:2301-2306`, `A:2365-2370`), `holder-unreachable` (`A:2309-2316`), `no-session` (`A:1879-1883`), `holder-socket-missing` (`A:1886-1892`); `result: refused, reason: preserve-unsupported` (`A:2220-2227`) | C1 |
| out | record `state` `stopping` then `stopped` | `H:5557-5558`, `H:5587-5588`; dead-holder path rewrites `state: stopped` only once nothing is left (`A:2277-2286`) | C1 |
| out | `events.jsonl` line `{"kind":"holder_instance_mismatch","op","expected_holder_instance_id"}` | C3 event stream | C3 (`H:4636-4637`) |
| out (proof) | `status` | `op_or_holder_lost(..., "state")` (`A:6114-6115`) → `outcome: stopped, residual_pids: []` (`A:1842-1857`); `list --include-dead` row `state: stopped` (`A:891`) | C1 |

## Invariants

- **I1 — A refused exact stop changes nothing.** Boundary: one live holder. The instance check
  runs before `stop_requested`, the state write, the permission cancel or any signal
  (`H:5533-5539`). The refusal says `mutation_status: not_started` (`H:4635-4650`).
- **I2 — Only identity-proven processes are signalled.** Boundary: CORE process identity.
  - The agent group counts for a signalling caller only while its live leader has the recorded
    start time (`verified_only`, `A:2018-2035`).
  - A child group counts only while a recorded member pid holds its recorded start time
    (`A:2036-2055`, `H:5654-5658`).
  - A live holder pid is signalled only when its argv names this record directory
    (`A:1774-1792`, `A:2307-2317`, `A:2374-2389`).
  - An argv that cannot be read never licenses a signal (`A:1783-1784`, `A:2308-2316`).
- **I3 — A holder that answers is never signalled.** Boundary: one live holder. A force stop on a
  silent socket first looks for the socket the holder's argv names. If one answers, the stop is
  sent there; if it answers as another instance, the stop is refused (`A:2357-2373`).
- **I4 — `stopped` alone is not proof.** Boundary: the stop receipt vs the process table. The
  holder reports `stopped: true` together with whatever `residual_pids` it measured
  (`H:5583-5596`). The dead-holder sweep does the same (`A:2248-2258`). The reused-pid path
  reports `stopped: not leftover` (`A:2347`). `status` says `outcome: stopped` only for a dead
  holder whose record says `stopped` and whose recorded groups have no live member
  (`A:1842-1857`). The dead-holder path
  writes `state: stopped` only when nothing is left (`A:2277-2286`).
- **I5 — A record is moved aside only when it is still the one read.** Boundary: the record
  directory. `retire_record` compares the current file with the record it read first
  (`A:2194-2203`), so a newer same-name record is never retired. The same compare guards the
  dead-holder `state: stopped` rewrite (`A:2279`).
- **I6 — Dispatched workers survive only by explicit intent.** Boundary: the dispatcher's process
  tree vs each worker's own tree. A Sideagent's stop always spares its workers; a Host's stop
  spares them only with `--preserve-dispatched-workers`; every other leftover group is swept
  (`H:5659-5668`, `A:2056-2064`). A live holder without `preserve-dispatched/1` refuses the intent
  before anything is signalled (`A:2210-2227`).
- **I7 — A carrier's node ends with the carrier.** Boundary: C1 carrier ↔ C6 node. `_reclaim_node`
  runs in every stop mode, waits for a node start still in flight, and stops the node by its own
  holder instance (`H:3958-3980`, `H:3907-3956`). An unconfirmed node stop becomes a
  `stop-unconfirmed` maintenance failure, not silence (`H:3945-3950`).
- **I8 — A stop always ends its holder.** Boundary: the holder process. A stop reply carries
  `_exit_after_reply`, and the holder exits after sending it even when the caller has stopped
  waiting (`H:5596`, `H:5876-5889`).
- **I9 — The instance binding of I1 holds only while the holder is alive.** Boundary: CORE
  identity on a dead holder. **Nothing enforces it there.** With a dead holder,
  `op_or_holder_lost` calls `force_kill_from_record` for any stop (`A:1874-1876`). That function
  takes no expected id (`A:2230-2287`). See gaps S1 and S2.

## Dependency contracts

Each bullet is one seam: provider → consumer, contract version, and the suite or gap. A suite is
named only where I read an assertion that exercises the seam. "Shared path" means the assertion
goes through another command or a direct function call that reaches the same code.

**C1 internal (Runner CLI → holder `stop` op)**

- C1 CLI exact stop → live holder `op_stop` (I1): a foreign id is `holder-instance-mismatch`,
  `mutation_performed: false`, and the same instance is still serving and not `stopping`; the
  verified id stops; an omitted id keeps the old behaviour; `--force` honours the check too; the
  shared `kaola-tmux.sh` entry forwards the id
  (`test_stop_with_a_foreign_instance_id_is_refused_with_no_side_effect` … `test_shared_entrypoint_forwards_the_expected_instance_to_stop`,
  :469-523). suite: test-issue-73-canonical-root.py
- C1 holder cooperative stop → agent `session/close` when advertised
  (`test_object_caps_close_sent_on_stop`, :287-292). suite: test-acp-holder-continue.py
- C1 holder group sweep → `residual_pids: []`, with a stubborn child really gone
  (`test_stop_leaves_no_residual_pids`, :569-583). suite: test-acp-contract.py
- C1 holder sweep of detached out-of-group children (Claude Code bridge): a healthy bridge, a
  bridge that died first, and a holder lost with it (record-based)
  (`test_force_stop_sweeps_detached_claude_groups`, :359-497; `swept_child_pgids` at :405-465).
  This drives `--force`; the cooperative path reaches the same `_terminate_group`. suite:
  test-issue-50-runner-integration.py
- C1 holder `_exit_after_reply` (I8): after a stop answered over the socket, the holder pid is
  waited out (`test_m1_other_spelling_of_the_root_reaches_the_live_holder`, :1361; test-266
  composed "Host holder gone", :355). A caller that gives up before the reply is not exercised.
  suite: test-acp-contract.py

**C1 ↔ CORE identity (record directory, holder argv anchor, process-group identity)**

- CORE identity → C1 force stop of a silent holder (I2, I3): a reused holder pid is never
  signalled and the record is retired (`test_t4_reused_pid_is_never_live_and_never_signalled`,
  :1128-1160); its surviving agent group is swept first
  (`test_reused_pid_stop_sweeps_surviving_agent_group_before_retiring`, :1162-1182); an argv that
  names this directory gets SIGTERM/SIGKILL (`test_wedged_holder_without_socket_is_stopped_by_its_argv_anchor`,
  :1330-1340); another root spelling reaches the answering socket and the holder is not signalled
  (`test_m1_other_spelling_of_the_root_reaches_the_live_holder`, :1342-1364); a foreign answering
  instance is refused (`test_l3_argv_socket_answering_as_another_instance_is_never_stopped`,
  :1557-1572, in Issue132AnchorUnitTests); an unreadable argv gives `holder-unreachable`, sends
  no signal and keeps the record (`test_n6_unreadable_argv_holds_the_root_and_refuses_the_stop`,
  :1444-1463, a direct `force_stop_unreachable` call). suite: test-acp-contract.py
- CORE identity → C1 unverified agent pgid (I2): never signalled, only this seat's record retired
  (`test_i191_force_stop_never_signals_an_unverified_agent_group`, :1184-1262;
  `test_i191_reused_pid_stop_never_signals_an_unverified_agent_group`, :1510-1533, Issue132AnchorUnitTests). suite:
  test-acp-contract.py
- CORE record compare → C1 `retire_record` (I5): a newer record is never retired
  (`test_i191_reused_pid_stop_never_retires_a_newer_record`, :1535-1555); a surviving group keeps
  the record (`test_n6_reused_pid_stop_keeps_the_record_while_a_group_survives`, :1574-1590).
  suite: test-acp-contract.py
- CORE identity → C1 instance check on a silent live holder: a mismatched `--force` writes
  nothing and keeps the record (`test_stop_force_mismatch_on_unreachable_holder_writes_nothing`,
  :1281-1289). suite: test-acp-contract.py
- CORE identity → C1 dead-holder sweep with the *matching* id: the orphaned agent group is killed,
  the socket unlinked and `status` reads `stopped` with no residual
  (`test_t7_dead_holder_force_stop_sweeps_and_proves_gone`, :1291-1328). suite:
  test-acp-contract.py
- CORE identity → C1 dead-holder stop with a **foreign** expected id. suite: none (gap: S1 — the
  dead-holder branch (`A:1874-1876`) never compares `--expected-holder-instance-id` with the
  record (`A:2230-2287` has no such parameter), unlike the silent-live branch (`A:2300-2306`).
  Every dead-holder stop in the suites passes the matching id or none. Measured probe at this
  commit: a dead holder whose record names instance X, an identity-verified orphan agent group,
  `stop --expected-holder-instance-id 000…0` (no `--force`) → `stopped: true, holder_lost: true,
  force_killed_pids: [<orphan>]`, orphan gone, record rewritten `state: stopped`. Whether this is a
  defect is a Host judgment: only processes the record's own identity proves are touched (I2), but
  the I1 "refused instead of stopped" promise (`A:6185-6187`,
  `workflow-worktree.md:34-38`) does not hold once the holder is dead. Tracked in #289)
- CORE identity → C1 dead-holder stop **without** `--force`. suite: none (gap: S2 — the same
  branch sweeps whether or not `--force` was given; the docstring says "stop --force path when the
  holder is already gone" (`A:2232`). The S1 probe ran without `--force` and swept. The preserve
  docstring treats a Runner sweep of a dead holder as normal (`A:2211-2214`), so this may be the
  intent and only the docstring is narrow. No suite runs a non-force stop on a dead holder.
  Tracked in #289)

**C1 ↔ C3 (events)**

- C1 refused exact stop → C3 `events.jsonl` `holder_instance_mismatch` event (`H:4636-4637`).
  suite: none (gap: S3 — `grep -rn holder_instance_mismatch tests/` is empty; every mismatch
  assertion reads the receipt's `error`, never the event stream. It is the only trace a refused
  stop leaves for `observe`/`follow`. Tracked in #289)

**C1 ↔ C6 (Sideagent node and dispatched workers)**

- C1 carrier stop → C6 node reclaim (I7): a stopping carrier stops its running node by that node's
  holder instance and starts no new one; a node start in flight, or one slower than the stop, is
  still found and ended (`test_a_stopping_carrier_ends_its_running_node_and_starts_none`,
  `test_a_node_start_in_flight_ends_with_the_stopping_carrier`,
  `test_a_start_slower_than_the_stop_is_found_by_its_record`, :3428-3464). An unconfirmed node
  stop is logged `sideagent_node_stop_unconfirmed` and blocks a competing node
  (`test_an_unconfirmed_stop_blocks_a_competing_node`, :3373;
  `test_a_stopped_record_is_not_a_stopped_node_until_its_holder_is_gone`, :3385). These drive
  `_reclaim_node` and the node stop directly against a fake node socket, not through `op_stop`.
  suite: test-issue-255-lifecycle-state.py
- C1 stop → C6/C5 dispatched worker trees (I6): preserve keeps the complete worker tree and sweeps
  only the unrelated group; without the intent a Host stop sweeps as before; a Sideagent keeps a
  worker that names it as dispatcher (`test_preserve_keeps_the_complete_worker_tree_on_cooperative_stop`,
  `test_preserve_on_dead_holder_cleanup_and_default_stop_unchanged`, :3522-3540;
  `test_a_worker_naming_this_sideagent_as_dispatcher_is_kept_without_a_spawn_line`, :1902). suite:
  test-issue-255-lifecycle-state.py
- C1 preserve feature advertisement → C1 CLI refusal (I6): a live holder without
  `preserve-dispatched/1` gives `preserve-unsupported`/`not_started`; a dead one does not; the
  Runner forwards the flag only when given (`test_a_live_holder_without_the_feature_refuses_the_preserve_intent`,
  :3542-3562; `test_stop_and_drain_restart_forward_the_intent_only_when_given`, :3570-3595). suite:
  test-issue-255-lifecycle-state.py
- C1 Host stop with preserve → a real dispatched Worker keeps running after the Host holder is
  gone, and both the Host stop and the later Worker stop report `residual_pids: []` (:351-362).
  suite: test-issue-266-launch-broker-composed.py

**C1 → C4 (stop proof consumed by `state retire --live`)**

- C1 `status` proof of a stop (I4): a dead holder with `state: stopped` and no residual reads
  `outcome: stopped`; a live spawn-recorded child makes it `holder_lost`
  (`StoppedStatusTests.test_normal_stop_is_distinct_from_loss`, :2480-2565, a direct
  `holder_lost_receipt` call; end to end after a stop at :1322 and :1363). suite:
  test-acp-contract.py
- C1 `list` default omits a stopped seat (`A:891`). suite: test-acp-contract.py (asserted at
  :1312-1313; the pilot's :1310-1312)
- C1 stop proof → C4 `state retire --live`. suite: none (gap: the pilot's G9, unchanged. Re-measured
  at this commit: after a clean exact stop, `list --repo` → `[]`, `list --repo --include-dead` →
  `[(session, "dead", "stopped")]`, `status` → `outcome: stopped, residual_pids: []`. The Host
  reference still names `list --repo` as the `$LIVE` source
  (`templates/orchestrator/references/dispatch-collect.md:60-61`))

**Not crossed by this unit:** `drain-restart`'s idle stop (`require_idle`, `H:5540-5554`) belongs
to drain-restart and is not part of this pack. `grep -rn require_idle tests/` is empty, which is
recorded here for whoever writes that pack, not as a gap of this one.

## Acceptance

Observable outcomes. Each is asserted by the suite named in the matching contract bullet, unless
it is marked as a gap.

- An exact stop of a live holder with its own id gives `stopped: true`. A later `status` gives
  `outcome: stopped, residual_pids: []`. `list --include-dead` shows the seat `stopped`, and the
  default `list` does not show it.
- An exact stop with a foreign id on a live holder gives `holder-instance-mismatch`,
  `mutation_status: not_started`, and the holder keeps serving in its previous state.
- `--force` on a silent holder:
  - argv names this record → the holder is signalled, `holder_force_killed`;
  - argv names another process → `pid_reused`, nothing signalled, record retired, `status` →
    `no-session`;
  - argv unreadable → `holder-unreachable`, nothing signalled;
  - another spelling answers → the stop goes there (`answering_socket`).
- A dead holder: its identity-proven groups are swept, `holder_lost: true`, `residual_pids: []`,
  socket unlinked, record `state: stopped`. A foreign expected id does **not** refuse (S1), and
  `--force` is not needed (S2).
- Preserve: a live holder without `preserve-dispatched/1` refuses with `preserve-unsupported`; with
  it, dispatched worker trees survive in `spared_child_pgids`.
- A carrier stop ends its own Sideagent node and starts none; an unconfirmed node stop is a
  `stop-unconfirmed` maintenance failure.
- A refused stop writes one `holder_instance_mismatch` event (S3).

## Expected-change surface

This is planning information only. Legitimate work outside it is coordinated with the owner, and
never refused.

- C1 CLI: the `stop` branch and `op_or_holder_lost` (`A:6184-6199`, `A:1869-1904`);
  `force_kill_from_record`, `force_stop_unreachable`, `preserve_refusal` (`A:2206-2389`). S1 or S2,
  if the Host judges them defects, land here (an expected-id compare before the dead-holder sweep,
  or a corrected docstring).
- C1 holder: `op_stop`, `_terminate_group`, `_holder_instance_mismatch` (`H:5532-5596`,
  `H:5627-5692`, `H:4635-4650`). A holder change is a holder change for running seats: the release
  convention's `git diff OLD NEW -- scripts/kaola-acp-holder.py …` test applies (AGENTS.md
  "Commands", Release).
- CORE identity, read-only for this unit unless I2 changes: `recorded_groups`,
  `dispatched_worker_groups`, `holder_argv_anchor`, `retire_record` (`A:1968-2203`, `A:1774-1792`).
- C6: `_reclaim_node`, `_stop_node` (`H:3907-3980`).
- Suites: test-acp-contract.py (Issue132HolderIdentityTests, Issue132AnchorUnitTests), test-issue-73-canonical-root.py
  (exact stop), test-issue-255-lifecycle-state.py (preserve, node). Fixtures for S1–S3 would land in
  test-acp-contract.py next to `test_t7_dead_holder_force_stop_sweeps_and_proves_gone`, which
  already builds a dead holder with an identity-verified orphan. Phase 2 (#281) owns the pilot's
  gaps; S1–S3 are tracked in #289.
- Docs: `templates/SKILL.md.tmpl:131-133` and `templates/orchestrator/references/workflow-worktree.md:34-38`
  if S1's outcome changes what "exact" promises for a dead holder. That is a template change,
  rendered as usual.
- P1 module moves (#275–#277) may relocate these functions; the pack owner then refreshes the
  citations, and the pack never blocks the move (design §7).

## Evolution

- **Split signal (C1 / CORE identity).** Today the identity proofs (`recorded_groups`,
  `holder_argv_anchor`, start-time checks) live in the C1 CLI module and are duplicated in spirit
  on the holder side (`H:584`, `H:604`; `A:2097`). If a second consumer needed them — for example
  a sweep tool outside `kaola-acp.py` — that would argue for moving them behind the CORE boundary
  the modular-core design already names. Evidence that would trigger it: a change that has to
  edit both `A:2097` and `H:584` for one identity rule.
- **Merge signal.** None: the CLI and holder are separate processes with a socket protocol
  between them; they stay two sides of one seam.
- **Language signal (C1 "retire" vs C4 "retire").** Confirmed again here: C1's
  `retire_record` renames a session record so `status` reads `no-session` (`A:2194-2203`); C4's
  `state retire` deletes a task/hold/alert/decision row (pilot). Same rule as the pilot: if one
  module ever needs both, rename one.
- **Language signal ("stopped").** The receipt key and the record state share a word but not a
  meaning (I4). If a consumer starts treating the receipt's `stopped: true` as proof, rename the
  receipt key or document it at the consumer; evidence would be a consumer that reads `stopped`
  without `residual_pids`.
- **Retire this pack** when S1 and S2 are decided in #289 and either fixed with fixtures or
  documented as intended, and P1 has moved these functions; refresh it instead if the cut lines stay. It then
  stays in Git history.

## Evidence

- Commit: `4c30b71d0b964628c5a39159ff0cd89504adcd6b` (main, merge of #280). Source is identical to
  the pilot's `8b3779c9` for `scripts/`, `tests/`, `templates/`, `platforms/`.
- Source read: `scripts/kaola-acp.py:804-843, 867-895, 1754-1792, 1825-1904, 1968-2389, 5895-5901,
  6114-6115, 6184-6199`; `scripts/kaola-acp-holder.py:39-48, 248, 257-258, 584-610, 1995-2035,
  3907-3980, 4629-4650, 5532-5692, 5832-5833, 5876-5889`;
  `templates/SKILL.md.tmpl:125-140`; `templates/orchestrator/references/workflow-worktree.md:30-38`;
  `templates/orchestrator/references/dispatch-collect.md:58-61`;
  `kpm/docs/history/kpr/docs/designs/modular-core-2026-10-07/design.md:26-33` (C1/C3 rows).
- Suites read for seam coverage (all in `./scripts/validate.sh --list`):
  - test-acp-contract.py (AcpContractTests :354, Issue132HolderIdentityTests :1043,
    Issue132AnchorUnitTests :1384, StoppedStatusTests :2480)
  - test-issue-73-canonical-root.py (:469-523)
  - test-acp-holder-continue.py (:287-292)
  - test-issue-50-runner-integration.py (:359-497)
  - test-issue-255-lifecycle-state.py (:1902, :3373-3400, :3428-3464, :3522-3595)
  - test-issue-266-launch-broker-composed.py (:351-362)

  Also grep-checked for the refusal and event names: `holder_instance_mismatch` (no test),
  `holder-socket-missing` (no test), `require_idle` (no test; drain-restart, not this unit).
- Probe: one scratch script outside the repository (`/tmp/i283-probe/probe.py`), run at this
  commit against `tests/contract/mock-acp-agent.py` with a temp git repo and record root; it wrote
  no repository file and stripped `KAOLA_*` from the caller environment as the suites do.
  - Clean exact stop: `stopped: true, residual_pids: [], mutation_status: not_started`; `status` →
    `outcome: stopped`; `list` → `[]`; `list --include-dead` → `[("probe-a","dead","stopped")]`; a
    second stop → `stopped: true, holder_lost: true, swept_pgids: []` (idempotent).
  - S1/S2: dead holder + identity-verified orphan + `stop --expected-holder-instance-id 000…0`
    without `--force` → `stopped: true, holder_lost: true, force_killed_pids: [<orphan>],
    residual_pids: []`; orphan gone; record `state: stopped`; recorded id ≠ expected.

Mirror citations: `kpm/…` paths = github.com/KaolaBrother/kaola-project-manager at fixed commit a13c6d6f264cf965ca45a07670dbf46cd1eb1e5f, subpath history/kpr/ — duplicate KPR source copies retired 2026-10-07; full mapping in `docs/kpm-transfer/HANDOFF.md`.
