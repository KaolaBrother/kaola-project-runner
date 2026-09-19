# Finalize observation: the intermittent `install-local.sh` hang, reproduced once

date: 2026-09-20
observed at: candidate `45f6c68` (the accepted tip), during the first finalize `./scripts/validate.sh`
machine: Darwin 27.0.0 arm64, GNU bash 5.3.9 (`/opt/homebrew/Cellar/bash/5.3.9/bin/bash`)

PR #100 flagged an "unreproduced intermittent `install-local.sh` hang" as an open, unresolved flag.
This finalize hit it once and captured the first live process evidence for it. The captured facts
are recorded here; the cause is **not** established and the fix is **not** attempted in this run.

## What was observed

`./scripts/validate.sh` stopped producing output after `installer migration acceptance: PASS` and
made no further progress for **13 minutes**, at which point the run was terminated
(`VALIDATE_EXIT=143`, SIGTERM — a killed background validate leaves no natural exit line).

Process tree at the moment of capture:

```
25825  bash tests/contract/test-installer-runtimes.sh                                  13:05
61737   \_ bash tests/contract/test-installer-runtimes.sh            (command-subst fork) 12:51
61738       \_ bash .../install-local.sh --runtime codex --platform grok,zcode --method link  12:51
62317           \_ bash .../install-local.sh --runtime codex --platform grok,zcode --method link  12:51
```

`62317` is the leaf: **state `S`, zero children, zero CPU growth.** Its descriptors:

```
0r  CHR  /dev/null                       <- not blocked on terminal input
1,2 PIPE ->0x76cab1a47a0de023            <- the harness output capture
3   PIPE 0xb93915ebd1dbfb2d ->0xa5c9932a20ed75eb
4   PIPE 0xa5c9932a20ed75eb ->0xb93915ebd1dbfb2d
```

Descriptors 3 and 4 are **the two ends of one pipe, both held by this single process**, which is
the shape bash 5.3 produces when it serves a here-document through a pipe instead of a temp file.

## Where it stopped

The fixture state pins the exact call. The test is `test-installer-runtimes.sh:795`, the first
`repo-user-hook` install. Inside the Codex destination, the installer had reached the first Skill of
its staging loop and left the staged symlink behind:

```
$tmp_root/user-hook-codex/skills/.grok-kaola-project-runner.tmp.61738
```

`.tmp.$$` is created immediately before `place_staged` at `scripts/install-local.sh:571`, and
`place_staged` (line 308) is exactly a here-document-fed interpreter call:

```sh
"$installer_python" - "$1" "$2" "$3" "${4:-0}" <<'PY'
```

So the run stopped in `place_staged`, at a here-document, with a self-held pipe pair and no
interpreter child ever appearing — consistent with the here-document write end never closing, which
is the Issue #78 class of defect. **This is a hypothesis from the captured descriptors, not a
proven cause: no stack was obtained** (`sample` was never run against the live pid before it was
killed, because `timeout` is not installed on this machine and the first attempt returned 127).

## Not caused by this change

- `scripts/install-local.sh` changes on this branch are three pure roster registrations
  (`--help` platform list, `skill_name_for` case arm, default `selection` array), `+5/-2`. None of
  them touches `place_staged`, the staging loop, or any here-document.
- The platform that hung is **`grok`**, not `dsh`, and the invocation was
  `--platform grok,zcode` — `dsh` was not in the selection at all.
- `tests/contract/test-installer-runtimes.sh` was then run standalone **three consecutive times**
  at candidate `27f3fe6`: `RUN1_EXIT=0`, `RUN2_EXIT=0`, `RUN3_EXIT=0`, each completing in well
  under the 400 s watchdog. The full `./scripts/validate.sh` was then re-run to completion.

## Disposition

Recorded, reported, and filed as a follow-up rather than repaired here: reproducing it took one
occurrence in roughly four full-suite runs, so a fix authored now could not be shown to work. The
follow-up carries these captured descriptors so the next occurrence does not start from zero.
