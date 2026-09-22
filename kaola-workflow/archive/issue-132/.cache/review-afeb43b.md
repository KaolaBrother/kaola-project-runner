VERDICT: ACCEPT_WITH_FINDINGS

Candidate: workflow/issue-132 @ afeb43b (base 428e7bb), reviewed as `git diff 428e7bb afeb43b -- ':!skills' ':!hosts'`
plus the rendered surfaces named in the brief. Reviewer made no change to the worktree or the main checkout.

Signal safety, which was the main question: I found no path that signals a process that is not provably
this record's holder (argv `--record-dir` anchor) or one of its identity-checked recorded groups. The
reused-PID fixture (T4) receives no signal, and an unreadable argv refuses. I did find one false-negative
race in `host-exists` (F1) and one orphan-hiding path in the reused-PID stop (F2).

Findings are ranked by severity, most severe first. Counts: 0 high, 3 medium, 4 low.

## F1 MEDIUM, CONFIRMED (reproduced): `host-exists` misses a second Host while the first holder is still initializing

- Code: scripts/kaola-acp.py:2291-2314 (`verified_hosts` counts only rows with `identity == "verified"`);
  scripts/kaola-acp-holder.py:3843-3877 (`run()` binds and listens on the socket, then calls
  `initialize_agent(...)`, which waits 15 s for initialize, 15 s for session/new or load, and up to 30 s for auth. The
  `accept()` loop starts only after that).
- What goes wrong: while Host A is inside `initialize_agent`, a connection to its socket succeeds but
  nothing answers. `holder_identity` waits 5 s and returns `unreachable`, so `verified_hosts` skips A.
  A concurrent `start` of a differently named Host B on the same canonical root therefore goes ahead,
  and both Hosts end up `verified`. That breaks invariant A1. A5 is supposed to be the mechanical
  fail-closed guard for exactly this case: two Delegators, or a Delegator plus a retry, starting at once.
- Reproduction (scratch record root /tmp/rv132.H5UW, mock agent wrapped in `sh -c 'sleep 12; exec …'`):
  `claude-code start --session claude-code-RVW-orchestrator-a` ran in the background. After 2 s, `list`
  showed `a unreachable host_class=True` and took 5 s. Then `start --session claude-code-RVW-orchestrator-b`
  returned rc 0 and `state: ready`, with no refusal. Final `list` showed `a verified 87658` and
  `b verified 93061`, i.e. two live Hosts. I stopped both myself with `stop --force`; no leak.
- Suggested fix: a Host row that is `unreachable` but whose PID argv anchors it to its record
  (`holder_argv_anchor(...) is True`) is a live holder of that record. It should block a
  second Host: refuse `host-exists` with `identity: unreachable`, or use a distinct typed refusal. This follows
  A5's fail-closed intent. Its literal text ("rows failing the check never refuse") assumed that a failing row
  means a dead or wedged holder. Serving `state` before `initialize_agent` would also close the window.

## F2 MEDIUM, CONFIRMED (reproduced): reused-PID `stop --force` retires the record and leaves live agent groups with nothing pointing at them

- Code: scripts/kaola-acp.py:1280-1297 (`force_stop_unreachable`, `anchor is False` branch).
- What goes wrong: the holder crashed and its agent group survived (the state T7 models). Its PID was then
  reused by an unrelated process. `stop --force --expected-holder-instance-id <id>` renames `record.json` to
  `record.pid-reused-<ts>.json` and unlinks the socket. It signals nothing, not even the identity-checked
  groups that `force_kill_from_record` would kill for a dead holder. It reports them only in
  `residual_pids`. After that, `status` reads `no-session`, which host-startup.md and handoff step 3 define as
  "proven gone". `list --include-dead` no longer shows the record, so no later sweep can find those
  processes.
- Reproduction (python fixture in /tmp/rv132b.*): the record had holder_pid = a live `sleep`, and
  agent_pid/pgid = a second `sleep` in its own session. Results:
  `stop {'stopped': True, 'pid_reused': True, 'signalled_pids': [], 'residual_pids': [44627]}`,
  then `status no-session`, then `agent alive: True`, then `list --include-dead` returned `[]`. I killed both sleeps myself.
- Note: `command_start`'s reused-PID branch (scripts/kaola-acp.py:2426-2450) correctly refuses via
  `holder_lost_receipt` when the agent is alive. The stop branch does not use the same care.
- Suggested fix: in the `anchor is False` branch, sweep `recorded_groups(record, directory)` exactly as
  `force_kill_from_record` does. Those groups carry their own pgid/lstart checks, and the holder is proven not to be a
  holder. Or keep the record, marked `stopped`, while `live_group_members(...)` is non-empty, so the orphan
  stays visible.

## F3 MEDIUM, CONFIRMED (mutation): the guard behind deviation (c) is untested, and it is the one that prevents spawning a second holder over a live one

- Code under test: scripts/kaola-acp.py:2432
  `if identity == "verified" or holder_argv_anchor(holder_pid, directory) is not False:`
- Test gap: tests/contract/test-acp-contract.py:1041-1204 (`Issue132HolderIdentityTests`).
- Mutation: in a scratch copy (/tmp/rv132mut.*, since deleted) I reduced that condition to
  `identity == "verified"`, which removes deviation (c). All 7 `Issue132HolderIdentityTests` still passed. Under
  that mutation, a same-name `start` on a live holder whose socket is missing or silent (an initializing
  holder, per F1, or the wedged holder in `test_wedged_holder_…`) would overwrite its record and spawn a second holder on
  the same record directory. Neither `holder_argv_anchor`'s `None` (unreadable argv) branch in `start` nor the
  `holder-unreachable` refusal in `stop --force` is exercised either.
- Suggested fix: add a test. Start a holder, unlink its socket, then run a same-name `start`. Expect
  `session-exists` with `error.identity == "unreachable"`, the same `holder_pid`, and no new holder process.

## F4 LOW, PLAUSIBLE (traced; the unreachable reading was reproduced, the kill was not): the sweep text stops `unreachable` rows directly with `--force`, which can include in-flight holders

- Text: templates/orchestrator/references/host-startup.md.tmpl, sweep table row
  "`dead` / `unreachable` (Host or worker) … | stop, prove gone", followed by
  "Stop = … `stop --force --expected-holder-instance-id`". Handoff step 3 has the same
  "`stop --force` with its record id".
- Problem: per F1, `identity: unreachable` also covers a holder that is still initializing: it read
  `unreachable` for about 12 s in my reproduction. For such a row, `stop --force` queues on the backlog and the holder
  force-stops itself once init finishes. If init exceeds the 30 s stop timeout, the reply is
  `holder-unreachable`, and `force_stop_unreachable` sends SIGTERM/SIGKILL through the argv anchor. Either way a
  starting session is killed, which contradicts the same section's "in-flight work is never guessed dead". Design A4 step 1 and
  B2 #8 called for a plain exact `stop` first, escalating to `--force` only when that also failed.
- Suggested fix: say "re-list once; stop `unreachable` only if it is still unreachable, plain stop before `--force`"
  (or rely on F1's anchored-unreachable classification).

## F5 LOW, CONFIRMED (text trace): handoff step 3 contradicts the host-startup table on `mismatch`, and it names only `$ZCODE`

- skills/kaola-delegator/references/handoff.md, Recover step 3: "A Host row failing identity is first
  exact-stopped (`stop --force` with its record id) and proven gone". "Failing identity" includes `mismatch`.
  skills/kaola-project-runner/references/host-startup.md says `mismatch` → "report, never stop".
  - In code, stopping a `mismatch` row goes over the socket to the answering holder. That holder refuses
    `holder-instance-mismatch`, so nothing unsafe happens. But step 3 can then never be satisfied, and the
    Delegator gets no instruction beyond "re-read `status`". This is a dead end, not a hazard.
- The only Runner defined in handoff.md is `$ZCODE` (the zcode Runner). The `list` rows are cross-platform, for example a
  dead `claude-code-KPR-orchestrator-x`. `"$ZCODE" stop --session claude-code-…` resolves
  `record_dir(zcode, …)` (scripts/kaola-acp.py:451-453, with no platform/session prefix check), which returns
  `no-session`. That is an accepted "gone" state, yet the real row was never touched. host-startup.md says
  "that platform Runner's `stop`"; handoff.md does not.
- Suggested fix: in step 3, limit the stop to `dead`/`unreachable` rows, send `mismatch` rows to
  report or HUMAN_DECISION_REQUIRED, and say to stop a row with its own platform's Runner.

## F6 LOW, CONFIRMED (measured): the default `list` view now pays up to 5 s per live row

- Code: scripts/kaola-acp.py:535 calls `holder_identity` on every row that is kept, and scripts/kaola-acp.py:914 sets
  `IDENTITY_PROBE_TIMEOUT = 5.0`. The probes run one after another.
- Effect: the frozen `kaola-acp-list/1` live view used by the external consumer (Kaola Terminal) used to cost
  at most a 0.5 s connect per row. Now each initializing or silent holder adds 5 s per `list` call. I measured
  5 s for one initializing row (F1 reproduction).
- Suggested fix: only probe when `socket_ok` is true and use a shorter bound for the default view, or probe
  rows in parallel.

## F7 LOW, PLAUSIBLE (trace): `mismatch` Host rows do not block a second Host

- scripts/kaola-acp.py:2306-2308. A `mismatch` row means a live holder is answering on that Host
  record's socket, just under a different `holder_instance_id` than the record's. `verified_hosts` skips it, so a
  second Host can start while that holder is live. This requires an earlier double-holder state, so it is rare.
  B2 #9 says "at least one of the two is a live real holder". Counting such a row as occupying, or refusing
  with its identity, would keep A1 fail-closed.

## T-item coverage

T1, T2, T3, T4, T5 (claude-code Host name under `KAOLA_ACP_DISPATCHER`), T6, T7, T8 (data sufficiency only, as
designed), T9, T11 and T13 are asserted. For T13 the check is keys, typed shape, and exit 1, with no comparison
against `canonical-root-*`. T12 is covered by the existing suites, which pass. Gaps:
- T10 is only partly asserted as designed. The handoff `list --repo` pin matches step 1, not step 3 as T10
  states. Step 3 itself is pinned only through the "proven gone" phrasing.
- T14 (live UAT on a real ZCode Host with the `swept:` line) has no evidence in the run folder.
- The deviation (c) guard and both unreadable-argv branches are not asserted (F3).

## Declared deviations

- (a) `--include-dead` opt-in: accepted. It honors the frozen live-only `kaola-acp-list/1` rows, and
  list-view.md, api.md and the Skill commands consistently pass `--include-dead`. See F6 for the latency the
  default view now pays.
- (b) Retiring a reused PID's record instead of marking it `stopped`: the reasoning holds, since a live reused PID
  would never let `status` read `stopped`. As implemented, though, it drops the only pointer to surviving
  agent groups (F2).
- (c) Keeping `session-exists` when argv is unreadable or anchored: correct, and the safe direction. It is untested (F3).
- (d) Holder records its inherited `dispatcher`: accepted. It is an additive record/list field, and
  `parse_dispatcher` enforces the same four-string shape as `dispatcher_identity`. T8 asserts it on a real dispatched
  seat.
- (e) T5/T13 in test-issue-74, T6 in test-acp-contract: accepted. They drive the real CLI start and list paths.
- (f) heartbeat-skeleton unchanged: accepted. C11 made that edit optional, and C7/C8 carry the obligation.

## Commands run

- `git -C <wt> log --oneline -3`, `git -C <wt> diff --stat|diff 428e7bb afeb43b -- scripts/ templates/ docs/ README.md CHANGELOG.md tests/`
- `grep`/`sed -n` reads of scripts/kaola-acp.py, scripts/kaola-acp-holder.py, scripts/kaola-acp-sweep.py, tests, and rendered skills
- `ps -p <pid> -o command=` (plain, `COLUMNS=80`, and with a pty on stdin) against live holder 9428: argv is not truncated
- Reproduction of F1 with a scratch `KAOLA_ACP_RECORD_ROOT=/tmp/rv132.H5UW`: two `claude-code start` runs, `list` twice, then `stop --force` of both (no leak)
- Reproduction of F2 with a python fixture under /tmp/rv132b.*: `list`, `grok stop --force`, `grok status`, `list --include-dead`; both sleeps killed by me
- `env $U python3 tests/contract/test-acp-contract.py Issue132HolderIdentityTests` → 7 OK
- Mutation in a scratch rsync copy /tmp/rv132mut.* (deleted afterwards): same class → 7 OK (F3)
- `env $U python3 tests/contract/test-issue-74-kaola-delegator.py` → 184 assertions, 0 failed
- `env $U python3 tests/contract/test-generated-skills.py` → PASS
- `env $U python3 tests/contract/test-progressive-disclosure.py` → 21 OK
- `pgrep -fl kaola-acp-holder` after the runs: none of my holders remain (the only worktree holder left, 50954, belongs to the concurrently running validate.sh root /tmp/kaola-val.YNvS7k)

(`$U` = the brief's `KAOLA_*` scrub, excluding `KAOLA_VALIDATE_*`.)
