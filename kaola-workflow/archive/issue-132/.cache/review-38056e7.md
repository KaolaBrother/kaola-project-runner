VERDICT: ACCEPT_WITH_FINDINGS

Candidate: workflow/issue-132 @ 38056e7 (base 428e7bb). Delta reviewed: `git diff edc4322 38056e7 -- ':!skills' ':!hosts'`.
I did not edit, stage or commit any tracked file. The only file I wrote is this handback. Scratch files are under /tmp/rv132f.

New finding counts: 0 high, 1 medium, 2 low, 1 informational.

## N1-N6 status

| # | Status | Evidence |
|---|---|---|
| N1 | FIXED (reproduced) | /tmp/rv132f/n1.py. A: claude-code mock Host `…-a` started with root `/tmp/rv132f/recN` (holder 37788, ready). B: a Host-named `start …-b` with root `/private/tmp/rv132f/recN` returned rc 1, `host-exists`, identity `unreachable`, and spawned nothing. Before the fix the argv mismatch freed the root. C: `stop --force --expected-holder-instance-id` under the `/private` spelling returned `holder_force_killed: 37788`, `pid_reused: None`, `residual_pids: []`, `stopped: true`. The reused-PID branch no longer reaches a live holder. Unit test `test_n1_anchor_matches_across_path_spellings` covers the `/tmp`, `/private` and symlink spellings. |
| N2 | FIXED (reproduced) | /tmp/rv132f/sb2.py, root recS. The stale Host record's holder_pid was a live own-user `sleep 122`, with no socket. Under `sandbox-exec -p '(version 1)(allow default)'`, a new Host start went ahead (`ready`, then stopped cleanly with `residual_pids: []`). A sandboxed `stop --force` of the stale record returned `pid_reused: true, holder_signalled: false, stopped: true`, and the reused sleep was still alive. Residual gap for PIDs owned by another user: see L1. |
| N3 | DOCUMENTED, not changed | docs/api.md:396-398 now says "the agent's recorded process group, plus child groups that still match their recorded start time". The wording is accurate. Behaviour is unchanged: `agent_pgid` is still swept without an identity check. This is the same gap the dead-holder path already had. |
| N4 | FIXED | host-startup.md.tmpl:86-88 now reads "may be live (only a dead or reused PID frees it)". Line 127 reads "`pid_reused: true` never signalled that reused PID", which is accurate, and the pin in test-generated-skills.py:643 was updated. |
| N5 | FIXED | README.md:65-69 and docs/zcode-host.md:503-507 now say mismatch is "reported for a human", matching the sweep table and handoff. `existing_host` now carries `answering_holder_instance_id` on mismatch (scripts/kaola-acp.py:2389-2391), and api.md documents it. |
| N6 | FIXED | `Issue132AnchorUnitTests` adds tests for an unreadable argv on both `verified_hosts` (the root is held) and `force_stop_unreachable` (`holder-unreachable`, no signal), and for the reused-PID survivor branch (`stopped: false`, record kept, residual reported, reused PID not signalled). All 13 Issue132 tests pass. |

## Brief question 2: `procargs_command` (scripts/kaola-acp.py:942-968) and the regex

I measured each case in /tmp/rv132f/pa.py, both unsandboxed and under Seatbelt:
- **Buffer parsing.** The layout is argc, then the exec path, then NUL padding, then argv. The function takes argc entries. Empty middle arguments (for example `--host-entry ""`) survive the split. A holder-shaped argv whose record dir contains a space and a non-ASCII argument came out identical to `ps`.
- **Huge argv.** 500 x 1000 B read back as 500656 characters.
- **Dead PID.** Returns None. `pid_alive` is false, so the anchor is False, as before.
- **Another user's PID (pid 1).** The sysctl gives EPERM, so procargs returns None. Unsandboxed, `ps` (setuid) still reads it, giving False. Under Seatbelt the anchor is None (see L1).
- **Zombie.** Unsandboxed, `ps` prints `<defunct>`, giving False. Under Seatbelt both readers fail and `pid_alive` is true, so the anchor is None (fail-closed).
- **Empty argv[0].** The `lstrip(b"\0")` swallows the empty argv[0]. The list then drops the last argument and includes the first environment string. `ps` on this Mac misparses the same case identically (both printed `30 CLAUDE_CODE_MESSAGING_TOKEN=…`). This is informational. A False→True flip would need a foreign process with an empty argv[0] whose first env string contains `kaola-acp-holder … --record-dir <this dir> --socket `, which is not realistic.
- **Wrong False for a real holder.** This needs the holder's argv to read successfully but not match. There is exactly one holder spawn site, scripts/kaola-acp.py:2534-2542: `[python, HOLDER, "--record-dir", dir, "--socket", sock, …]`, always in that order. `git log -S` shows this shape back to 13b5770. kaola-acp-sweep.py and the tests only read argv; they do not spawn holders. The only test fixture with a synthetic holder argv (test-acp-contract.py:1264) also uses that order. I found no path that yields a real holder argv without ` --socket ` after `--record-dir`.
- **What if a future holder argv lacked `--socket`?** The anchor would be False. The root would be freed and the reused-PID sweep would kill the live holder's agent group. That would be unsafe, but nothing produces such an argv today. A regex anchored on `--record-dir (.+?) --socket ` couples safety to argv order. That is worth a comment at the spawn site, but it is not a current defect.
- **Wrong True for a foreign process.** This needs the substring `kaola-acp-holder` plus a `--record-dir X --socket ` whose realpath equals this record dir, for example `sh -c "…kaola-acp-holder … --record-dir <dir> --socket …"` holding a reused PID. The previous code had the same weakness, and the combination is not realistic.
- **`ps` truncation.** `ps -o command=` from a non-tty with `COLUMNS=80` returned the full 341-character argv, so no truncation.

## New findings

### M1 MEDIUM. Mechanism CONFIRMED; trigger PLAUSIBLE. A caller that spells the record root differently sees a live, answering Host as `unreachable`, and the documented sweep escalates to `--force` against it
- Code: `sock_path_for_directory` (scripts/kaola-acp.py:465-468) hashes `str(directory)`, which is the caller's spelling. The holder was given the socket derived from the starter's spelling (:2537). N1 fixed only the argv side. The socket path is still spelling-dependent. It also depends on `tempfile.gettempdir()` in the caller.
- Reproduction (/tmp/rv132f/n1.py): Host A was ready and answering under `/tmp/rv132f/recN`. Under `/private/tmp/rv132f/recN`, `start …-b` reported A's identity as `unreachable`. It never reached A's socket.
- Consequence: host-startup's sweep (templates/orchestrator/references/host-startup.md.tmpl:125-126) says: stop with `--expected-holder-instance-id`, `--force` "when that fails". A plain stop from the skewed caller cannot reach the socket and fails. `--force` then SIGKILLs the live holder (`holder_force_killed: 37788` in the reproduction). A healthy Host with in-flight work is killed, against "in-flight work is never guessed dead". Before N1 this path killed the agent groups instead, so the outcome is the same.
- Trigger: two Agents on one Mac whose `KAOLA_ACP_RECORD_ROOT`, or whose `TMPDIR`/`XDG_RUNTIME_DIR`, name the same directory through different spellings (for example `/var/folders/…` versus `/private/var/folders/…`). This is uncommon, but #132 is the first change that acts on `unreachable` automatically.
- The root cause predates #132. The sweep is new.
- Suggested fix: resolve the directory in `record_root`/`sock_path_for_directory`, or read the socket path from the live holder's argv `--socket`, before a silent verdict licenses `--force`. Resolving it would move socket paths for holders already running. This is a compatibility decision for the owner.

### L1 LOW. Mechanism CONFIRMED; trigger PLAUSIBLE. Residual of N2: under Seatbelt, a stale Host record whose PID was reused by another user's process (or is a zombie) still blocks the root
- `process_command` → `ps` cannot exec under Seatbelt. `procargs_command` gets EPERM for a PID owned by another user and EINVAL for a zombie. `pid_alive` is true, so `holder_argv_anchor` returns None (:995-996). `verified_hosts` then holds the root and `force_stop_unreachable` refuses `holder-unreachable`.
- Measured: under `sandbox-exec`, `holder_argv_anchor(1, dir)` returned None (unsandboxed it returns False). The zombie case also returned None under the sandbox.
- This fails closed, as the docs describe ("an unreadable argv refuses"). The way out is an unsandboxed stop, which the refusal text does not mention.
- An optional refinement: the libproc `PROC_PIDTBSDINFO` path already present (`_BsdInfo`, :1129) could report the process's uid. A uid different from the caller's would prove the process is foreign.

### L2 LOW, CONFIRMED (read). `holder_argv_anchor`'s safety depends on the argv order `--record-dir` then `--socket`
- The regex at scripts/kaola-acp.py:983 returns False, which is treated as "provably another process", for any holder argv that does not follow `--record-dir` with `--socket`. The only spawn site (:2534-2542) complies today. Nothing pins that coupling, whether a comment at the spawn site or a test that builds the argv from `command_start`. A future reorder would silently turn a live holder into a "reused PID" whose groups get swept.
- Suggestion: parse with `shlex`-free token matching, as kaola-acp-sweep.py `flag_value` does, or add a test that runs the real spawn argv through the anchor.

### I1 INFORMATIONAL. An empty argv[0] shifts the parsed argv by one entry
- See the empty argv[0] case in question 2. `ps` on this Mac behaves identically, and I found no safety consequence.

## Brief question 3: any HIGH in 428e7bb..38056e7 missed by earlier rounds
None found. M1 is the most serious remaining item. It is fail-open only in the sense that a documented operator or Host step kills a live Host. The code itself fails closed: it refuses `host-exists` rather than starting a second Host.

## Commands run
- `git log --oneline -5`; `git diff --stat edc4322 38056e7 -- ':!skills' ':!hosts'`; `git diff edc4322 38056e7 -- ':!skills' ':!hosts' ':!tests'` and `-- tests`
- `grep -rn -- '--record-dir' scripts tests`; `sed -n 2520,2560p scripts/kaola-acp.py`; `git log --format=%h -S'"--record-dir", str(directory)'`; `grep` reads of `record_root`, `sock_path*`, `pid_alive` and `PS_ENV`
- `ps` truncation probe: a Python child with a 341-character argv, read with and without `COLUMNS=80`
- `python3 /tmp/rv132f/pa.py`, and the same under `sandbox-exec -p '(version 1)(allow default)'`, loading scripts/kaola-acp.py as a module. It tests the holder-shaped argv, huge argv, empty argv[0], pid 1, zombie and dead PID. Every child was killed in `finally`.
- `env $U python3 /tmp/rv132f/sb2.py <wt>/scripts/kaola-acp.py /tmp/rv132f/recS /tmp/rv132f/repo` (N2)
- `env $U python3 /tmp/rv132f/n1.py <wt>/scripts/kaola-acp.py /tmp/rv132f/repo` (N1 and M1)
- `env $U python3 tests/contract/test-acp-contract.py Issue132AnchorUnitTests Issue132HolderIdentityTests`: 13 tests OK
- `env $U python3 tests/contract/test-generated-skills.py`: PASS
- `env $U python3 tests/contract/test-issue-74-kaola-delegator.py`: 185 assertions, 0 failed
- `env $U python3 tests/contract/test-progressive-disclosure.py`: OK
- `scripts/render-skills.py --check`: PASS
- Leak check with `pgrep -fl rv132f`, `mock-acp-agent` and `sleep 122`. None of my processes remain: holder 37788 is gone, recS Host `…-new` was stopped with `residual_pids: []`, and the reused sleep was killed. The only live holder and mock processes are the running validate.sh's (`/tmp/kaola-val.AW7WDZ`).

(`$U` is the brief's `KAOLA_*` scrub, which excludes `KAOLA_VALIDATE_*`.)
