# Issue #78 root cause: bash here-document self-deadlock on a macOS degraded pipe

## The mechanism

1. Bash (Homebrew `bash 5.3.9(1)-release`, which `#!/usr/bin/env bash` resolves to at
   `/opt/homebrew/bin/bash`) implements a here-document whose body is <= its compile-time
   `HEREDOC_PIPESIZE` (4096 bytes) by creating a pipe and writing the whole body into it,
   then handing the read end to the command as stdin. The write happens in the forked
   child *before* `exec`, so the same process holds both ends and nothing is draining.
2. If the body does not fit in the pipe buffer, that `write()` blocks forever. Self-deadlock.
3. macOS degrades pipe capacity under system-wide pipe-KVA pressure. Measured on this Mac:

       held_pipes  fresh_pipe_capacity
                0  65536
               50  65536
              100  65536
              150  512      <- fell below the 1039-byte usage() heredoc
       released all held pipes; capacity now: 65536

   So under load a fresh pipe can carry only **512 bytes**, while bash still believes
   anything up to 4096 is safe to push in one write.
4. Every here-document in these scripts between 513 and 4096 bytes therefore deadlocks
   whenever it happens to get a degraded pipe.

## Direct evidence: five real stuck processes, sampled live

`sample` of processes that were already hung on this machine (none of them started by
this run; they belong to other runs and were only read, never signalled):

    pid 69044  bash ... kaola-tmux.sh claude-code status --help     stuck 1d 10h
      main -> reader_loop -> execute_command_internal -> execute_case_command
           -> execute_simple_command -> execute_builtin_or_function
           -> execute_function            <- usage()
           -> execute_disk_command        <- cat
           -> do_redirections -> do_redirection_internal
           -> heredoc_write -> write  (in libsystem_kernel.dylib)

Top-of-stack for all five:

    sample-21114  read    (in libsystem_kernel.dylib)   <- top-level bash, reading a command-substitution pipe
    sample-21117  __wait4 (in libsystem_kernel.dylib)   <- subshell waiting for its child
    sample-21118  write   (in libsystem_kernel.dylib)   <- heredoc_write, 1 heredoc frame
    sample-62005  write   (in libsystem_kernel.dylib)   <- heredoc_write, 1 heredoc frame
    sample-69044  write   (in libsystem_kernel.dylib)   <- heredoc_write, 1 heredoc frame

The three-process chain `21114 -> 21117 -> 21118` (identical argv at every level,
`ps` cannot tell them apart) decodes exactly as: top-level bash blocked reading the
command-substitution pipe, the forked subshell blocked in `wait4`, and the pre-exec
fork child blocked in `heredoc_write`.

## Why this explains every reported fact

- **Load dependence, and no failure below load ~6.7**: the degraded 512-byte pipe only
  appears under system-wide pipe pressure.
- **Blocks at spawn and consumes the entire 60 s**: the block is a permanent deadlock,
  not slow progress. Matches the `ps` lstart pairs exactly 60 s apart.
- **Only two of 29 cases, while the machine stayed fast**: each invocation deadlocks only
  if *its* pipe happened to be a degraded one; the other 27 cases ran normally in the
  same run. This is why total runtime was 24 s + 2x60 s = 145 s, not a uniform slowdown.
- **Orphan with identical argv and NO children, dying to a single SIGTERM**: the stuck
  process is the pre-exec fork child. It has not `exec`ed yet, so `ps` shows the parent
  script's argv; it has no children of its own; it is in interruptible `write`, so one
  SIGTERM ends it; and Python's `subprocess.run` timeout `kill()` reaches only the direct
  child, never this fork.
- **Refusal cases hang while accepting cases pass**: the refusal path ends in
  `refuse_canonical_root` -> `emit_json`, whose heredoc is **883 bytes** (> 512). The
  accepted path instead ends at `die "tmux executable not found"`, which is a plain
  `printf` with no heredoc at all. The cases that "did less work" hung precisely because
  the little they did included an 883-byte heredoc.
- **`install-local.sh` and `status --help` hang too**: same bash pattern, different script.
  `usage()` is 1039 bytes. This was never specific to the Issue #73 guard.

## Measured here-document sizes in scripts/kaola-tmux.sh

      line   21  EOF   1039 bytes   usage()                 RISKY
      line   41  PY     883 bytes   emit_json()             RISKY  <- the #78 failure
      line  121  PY     210 bytes   manifest default_transport
      line  343  EOF    212 bytes
      line  374  PY     523 bytes                           RISKY
      line  450  PY     333 bytes
      line  471  PY     909 bytes                           RISKY
      line  486  PY     451 bytes
      line  590  PY     287 bytes

## Repo-wide exposure

29 shell files contain 134 here-documents; **63 of them fall in the 513..4096 byte
deadlock window**, including `scripts/install-local.sh` (3) and ten `tests/contract/*.sh`
suites. The nine `skills/*/scripts/kaola-tmux.sh` copies are generated from
`scripts/kaola-tmux.sh` and inherit its four.

## What this refutes

- The issue's own hypothesis ("spending that long in process and `git` startup") - refuted.
- "Raise the `run_cli` timeout" - a deadlock has no finite timeout that helps.
- A generic retry - a retried invocation is equally likely to draw a degraded pipe, and
  each attempt leaks another permanently stuck process.
- Anything specific to `child_a`, to the Issue #73 guard, to ACP vs PTY, or to Issue #77.
