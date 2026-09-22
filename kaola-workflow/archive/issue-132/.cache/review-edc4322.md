VERDICT: ACCEPT_WITH_FINDINGS

Candidate: workflow/issue-132 @ edc4322 (base 428e7bb). Repair delta reviewed:
`git diff afeb43b edc4322 -- ':!skills' ':!hosts'`, plus the rendered handoff.md and host-startup.md.
I made no change to tracked files in the worktree or the main checkout. The only file I wrote is this handback.

Counts for new findings: 0 high, 2 medium, 4 low.

## F1-F7 status

| # | Status | Evidence |
|---|---|---|
| F1 | fixed | Re-ran the reproduction with scratch root /tmp/rv132e.78oI/rec and `mock-acp-agent.py` delayed by `sh -c 'sleep 12; exec …'`. At t+3 s, `list` showed `claude-code-RVW-orchestrator-a unreachable host_class=True`, taking 2.07 s. `start --session …-b` then returned rc 1, `host-exists`, `existing_host.identity: unreachable`, `holder_pid` 64587, and spawned nothing. A reached `ready` and was then `stop --force`d (`residual_pids: []`). With the fix reverted in a scratch copy, the new test-issue-74 F1 check fails. |
| F2 | fixed | Fixture: holder_pid is a live `sleep` (the reused PID), and agent_pid/pgid is a `sleep` in its own session. `stop --force` returned `pid_reused: true, holder_signalled: false, force_killed_pids: [orphan], residual_pids: []`. The orphan was dead afterwards and the reused PID was still alive. `status` read `no-session`. See N1 and N3 for what this new signal path now reaches. |
| F3 | fixed | `test_same_name_start_over_a_silent_anchored_holder_is_session_exists` fails when scripts/kaola-acp.py:2468 is mutated to `identity == "verified"`. The `None` (unreadable argv) branches are still unasserted; see N6. |
| F4 | partially | The table now says plain `stop` first, with `--force` only for `dead` rows or after a failed stop, and `unreachable` only on a second `list`. Nothing bounds how far apart the two lists must be. A holder can stay `unreachable` for up to about 60 s during init, while two back-to-back lists take about 4 s. The remaining risk is small, and the text now matches design A4. |
| F5 | fixed | handoff step 3: "by its own platform's Runner … report a `mismatch`". This matches the sweep table. |
| F6 | partially | The list probe is now 2 s per silent row (measured 2.07 s for one row). It is still sequential, so the cost grows linearly with the number of silent rows. |
| F7 | fixed | `mismatch` rows now occupy the root (scripts/kaola-acp.py:2337-2347). |

## New findings (most severe first)

### N1 MEDIUM. Mechanism CONFIRMED (reproduced); the trigger environment is PLAUSIBLE. The reused-PID sweep can SIGKILL a *live* holder's agent when the record root is spelled differently

- Code: the `holder_argv_anchor` match at scripts/kaola-acp.py:959 compares the holder argv's `--record-dir`
  token against `str(directory)` and `realpath(directory)` only. It never canonicalizes the argv side.
  `record_root` (scripts/kaola-acp.py:441-448) does not canonicalize either. As a result, a holder started with
  root `/tmp/X` is judged "provably another process" by a caller whose root is `/private/tmp/X`.
  The same applies to `/var/folders/…` versus `/private/var/folders/…` for the default `$TMPDIR` root.
- Regression: at afeb43b, the `anchor is False` branch signalled nothing. At edc4322
  (scripts/kaola-acp.py:1287-1300) it SIGKILLs every member of the record's groups.
- Reproduction (scratch /tmp/rv132e.78oI/rec4):
  1. `grok start` ran with `KAOLA_ACP_RECORD_ROOT=/tmp/…/rec4`, giving holder 48268 (argv `--record-dir /tmp/…`) and agent 48518.
  2. I unlinked the socket.
  3. `grok stop --force --expected-holder-instance-id <its id>` ran with `KAOLA_ACP_RECORD_ROOT=/private/tmp/…/rec4`.
  4. Result: `pid_reused: true, holder_signalled: false, force_killed_pids: [48518]`, and the record was retired.
  5. Afterwards the live holder 48268 had no agent, no record.json and no socket, so no Runner command could reach it. I killed it by hand after checking its argv.
- The same misclassification makes `verified_hosts` (scripts/kaola-acp.py:2339-2341) skip a live silent Host,
  and makes the same-name `start` replace a live holder's record. Both of those predate this repair.
- Suggested fix: compare `os.path.realpath` of the argv's `--record-dir` value as well, or record the holder's realpath in argv at spawn time.

### N2 MEDIUM, CONFIRMED (reproduced with a Seatbelt profile). A Seatbelt-confined caller is blocked permanently by a stale Host record whose PID was reused, and has no documented way out

- Code: `holder_argv_anchor` (scripts/kaola-acp.py:942-960) runs `ps` directly, not through `run_ps` with its
  libproc fallback. Under Seatbelt, even `(allow default)`, the setuid `/bin/ps` cannot exec
  (`sandbox-exec: execvp() of '/bin/ps' failed`), so every live PID yields `None`. The repaired
  `verified_hosts` treats `None` as "holds the root", and `force_stop_unreachable` refuses `None` with `holder-unreachable`.
- Reproduction (/tmp/rv132e.78oI/sb.py, scratch root rec3): a stale Host record `claude-code-RVW-orchestrator-old` has
  holder_pid set to an unrelated live `sleep` and no socket.
  - Under `sandbox-exec -p '(version 1)(allow default)'`, a new Host start returned `host-exists` with
    `identity: unreachable`, and `stop --force` returned `holder-unreachable`.
  - Outside the sandbox, the same stop gave `pid_reused: true` and freed the root.
  - At afeb43b the sandboxed start went ahead, because `unreachable` was skipped.
- Reach: a dsh Host's shell (Issue #120, Seatbelt-confined), or any Seatbelt-sandboxed Delegator. The refusal text
  ("exact-stop it and prove it gone") cannot be followed from inside the sandbox.
- Suggested fix: read argv through libproc (`KERN_PROCARGS2`) as a fallback, or document the unsandboxed stop as the way out.

### N3 LOW, PLAUSIBLE (simulated). The new reused-PID sweep kills `agent_pgid` without any identity check, although api.md calls the swept groups "identity-checked"

- `recorded_groups` (scripts/kaola-acp.py:1152-1154) appends `agent_pgid` unconditionally. Only the child groups
  carry lstart checks, and the holder records no agent start time (kaola-acp-holder.py:1445-1446, 1889-1890).
- Scenario: the reused-PID branch only runs once the holder's PID has already been recycled. If the old agent group also died, and its
  PID was recycled to an unrelated process that leads a group, every member of that group is SIGKILLed.
- Simulation (/tmp/rv132e.78oI/f2.py, case `pgidreuse`): the record's agent_pgid was an unrelated `sh -c 'sleep 121 & wait'`
  session. The stop reported `force_killed_pids: [84516, 84520]`, and that group was left empty.
- The dead-holder path `force_kill_from_record` had this gap before this change. The repair adds it to a branch that previously signalled nothing.
- The docs/api.md:394 wording "identity-checked groups" is inaccurate for the primary group.

### N4 LOW, CONFIRMED (text versus code). Two host-startup sentences are stale after the repair, and one of them is pinned

- templates/orchestrator/references/host-startup.md.tmpl:86-87 says `host-exists` refuses "while another Host-named
  holder … passes the identity check below". The code also refuses on `mismatch` and on `unreachable` rows
  that are anchored or have unreadable argv. Line 89, added by the repair, already says "else sweep it", so the paragraph contradicts itself.
- host-startup.md.tmpl:126 says "`pid_reused: true` signalled nothing and retired the record". The code now
  SIGKILLs the dead holder's groups (`force_killed_pids`), and when a survivor remains it keeps the record with `stopped: false`
  (scripts/kaola-acp.py:1287-1327). docs/api.md:394-397 and CHANGELOG were updated; this sentence was not.
  tests/contract/test-generated-skills.py:643 pins the stale phrase.

### N5 LOW, CONFIRMED (text trace). README and zcode-host.md tell the reader to stop a non-verified `existing_host`, while the sweep and handoff say to report a `mismatch`

- README.md:65-67 ("exact-stop and prove gone when it does not") and docs/zcode-host.md:505-507 ("else exact-stopped
  and proven gone first") cover `mismatch` rows too. host-startup's table row "`mismatch` | report, never stop" and
  handoff step 3 ("report a `mismatch`") contradict them.
- In code, a plain stop with the record's id against a mismatch row is refused by the answering holder
  (`holder-instance-mismatch`). A mismatch Host row therefore blocks every new Host until a human acts. That is fail-closed, but only
  the sweep and handoff say so.
- `existing_host` for a mismatch row reports the record's facts (scripts/kaola-acp.py:2342, `facts = record`), not the
  answering holder's `holder_instance_id`.
- docs/zcode-host.md:504-505 says "while its argv still names the record" for both silent and mismatch rows. The code
  blocks on mismatch regardless of argv, and on unreadable argv as well.

### N6 LOW, CONFIRMED (coverage read). The new branches that decide whether the root stays blocked are untested

- No test covers the reused-PID survivor branch (`leftover` non-empty, so `stopped: false` and the record is kept).
- No test covers `verified_hosts` with anchor `None`, or `force_stop_unreachable` with anchor `None`.
- The two new acp-contract tests do distinguish the fix from the bug, as shown by the mutations below, and both clean up:
  - The F2 test kills the orphan in `finally`.
  - The F3 test force-stops its holder, waits until it is gone, and clears `_started`.
  - The test-issue-74 F1 block registers the session before starting it, so `sandbox.cleanup()` stops it.

## Answers to the brief's specific questions

- A stale record whose PID is reused by a `kaola-acp-holder` of a *different* record: the argv holds a different
  `--record-dir` token, so the anchor is False and the record does not block. The `anchor is False` stop sweep skips `holder_pid`
  (scripts/kaola-acp.py:1295). It can still reach an unrelated process through a recycled `agent_pgid` (N3), and it can reach a
  live holder's agent through a path-spelling false negative (N1).
- `mismatch`: this is safe in the fail-closed direction. No signal path is reachable, because the stop goes over the socket and is refused. The only way out is a human (N5).
- A permanent block with no documented way out: yes, under Seatbelt (N2), and for `mismatch` rows unless a human steps in (N5).

## Commands run

- `git -C <wt> log --oneline -3`; `git -C <wt> diff --stat|diff afeb43b edc4322 -- ':!skills' ':!hosts'`
- `sed -n`/`grep -n` reads of scripts/kaola-acp.py, the tests, the rendered handoff.md and host-startup.md, README.md, docs/zcode-host.md, and docs/api.md
- F1 re-run: scratch `/tmp/rv132e.78oI` (git repo plus `KAOLA_ACP_RECORD_ROOT=$S/rec`). Ran a background `claude-code start …-a --command "sh -c 'sleep 12; exec python3 mock-acp-agent.py --scenario normal'"`, then `list`, `start …-b`, `list --include-dead`, and `stop --force` of a. An earlier attempt with fake-zcode-app-server.py produced `acp-initialize-failed`; I stopped that holder too.
- F2 plus N3: `/tmp/rv132e.78oI/f2.py`, cases `orphan` and `pgidreuse`. The first attempt at `pgidreuse` raised EPERM and left two `sleep 120`, which I killed.
- N2: `sandbox-exec -p '(version 1)(allow default)' /bin/ps …` (rc 71), and `/tmp/rv132e.78oI/sb.py`
- N1: `grok start` under `/tmp/…/rec4`, socket unlinked, `grok stop --force` under `/private/tmp/…/rec4`, then a manual `kill` of my own holder 48268 after checking its argv
- `env $U python3 tests/contract/test-acp-contract.py Issue132HolderIdentityTests` gave 9 OK
- `env $U python3 tests/contract/test-issue-74-kaola-delegator.py` gave 185 assertions, 0 failed
- `env $U python3 tests/contract/test-generated-skills.py` gave PASS; `test-progressive-disclosure.py` gave OK; `scripts/render-skills.py --check` gave PASS
- Mutations in the rsync copy /tmp/rv132mut2.jUAu (worktree untouched):
  - revert of the verified_hosts filter: the test-issue-74 F1 check fails
  - reused-PID sweep emptied: the F2 test fails
  - :2468 reduced to `identity == "verified"`: the F3 test fails
  - `test_existing_locator…` also failed in the copy, which is unrelated to these mutations; the locator does not resolve outside the real checkout
- Leak check: `pgrep -f kaola-acp-holder.py` with the argv `--record-dir` of each. Every remaining holder belongs to
  pre-existing live sessions under `$TMPDIR/kaola-501` or to the running validate.sh (`/tmp/kaola-val.QezIPG`). None of mine remain, and no `sleep 12x` processes remain.

(`$U` is the brief's `KAOLA_*` scrub, which excludes `KAOLA_VALIDATE_*`.)
