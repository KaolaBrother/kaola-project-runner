VERDICT: ACCEPT_WITH_FINDINGS

Candidate: workflow/issue-132 @ efc9c0c (base 428e7bb). Delta reviewed: `git diff 83052ce efc9c0c -- ':!skills' ':!hosts'`.
I did not edit, stage or commit any tracked file. The only file I wrote is this handback. Scratch files are under /tmp/rv132h.

New finding counts: 0 high, 0 medium, 1 low, 1 informational.

## Status of the prior findings

| # | Status | Evidence |
|---|---|---|
| M2 | FIXED (reproduced) | /tmp/rv132h/tz.py. The holder ran under the default TZ (CST +0800). The mock agent was wrapped as `sh -c '<mock>; exec sleep 300'` so its leader outlives the holder. The holder then got SIGKILL, and `stop --force` ran under a different TZ. Under `TZ=UTC` the receipt was `stopped: true, swept_pgids: [77278], force_killed_pids: [77278], residual_pids: []`, the agent was gone, and `status` read `stopped`. Under `TZ=America/New_York` it was `swept_pgids: [78549]` with the agent gone. The same-TZ control was also swept. The record held `agent_started: 1790054135.0`, a float. `residual_pids` is truthful in all three runs. At 83052ce the same UTC run left the agent alive. |
| L3 | FIXED (reproduced) | /tmp/rv132h/foreign.py. Without `--expected-holder-instance-id`, the command now returns `holder-instance-mismatch` and names the answering socket, both instance ids and nothing else. B stayed alive, the fake PID was not signalled, and no stop went to B. The run with the expected id refuses too (the record-level check). The code is scripts/kaola-acp.py:1438-1446. |
| I3 | FIXED | docs/api.md:390-392 now says 2 s per socket and 5 s for the guard, plus at most one more probe of the argv socket. |
| I2 | Unchanged, informational | Not in scope of this delta. |

## Brief question 1: DST and the libproc fallback

- **A DST transition between spawn and sweep is correct.** `strptime` sets `tm_isdst=-1`, so `mktime` applies the offset in force on the *date in the text*, not the current offset. Measured: in New York, a May spawn time round-trips to an exact epoch (delta 0.0). Within one TZ, both sides call `mktime` on identical text with the same libc, so they always agree, even in the repeated hour.
- **The repeated (ambiguous) hour across time zones is not handled.** See L4 below.
- **The spring-forward gap cannot occur**, because the text is rendered from a real instant.
- **The libproc fallback is consistent.** It uses `strftime('%a %b %e %H:%M:%S %Y', localtime(start_tvsec))` (scripts/kaola-acp-holder.py:119-120), which is the same text `ps` gives in the same TZ. Python's `%d` accepts the space-padded `%e` day. So a holder on the libproc path and a caller on the `ps` path, or the reverse, compare equal whenever `ps` and libproc would. The ambiguous-hour limit applies to both paths, because both go through local text.
- **The 1.0 s tolerance does no harm.** Both sides have second granularity, and current zone offsets are whole seconds, so a match is exact apart from the L4 case.

## New findings

### L4 LOW. CONFIRMED at unit level; the trigger is very narrow. A holder and caller in different time zones still disagree when the agent started in a repeated DST hour
- Code: scripts/kaola-acp-holder.py:350-355 (`start_epoch`) and scripts/kaola-acp.py:1273-1281. `lstart` text is local time with no offset, and `mktime(isdst=-1)` must pick one of the two instants for a repeated local hour. On macOS it picks the first (DST) one, so the second 01:30 in New York becomes the true epoch minus 3600.
- Measured (/tmp/rv132h/dst.py): true instant 1793514600, which is 2026-11-01 06:30Z. Under America/New_York the round trip is off by -3600.0. Under UTC, Asia/Shanghai and Europe/London it is off by 0.0. For the first 01:30 (1793511000) every zone gives 0.0.
- Reproduction through the real `recorded_groups` with a patched `run_ps` (/tmp/rv132h/dst2.py). A holder in New York recorded the epoch minus 3600, and the caller under `TZ=UTC` returned `included: False`. A holder under UTC with the caller in New York also returned `included: False`. Same-TZ pairs returned `included: True`.
- Consequence: this is the M2 symptom again. A surviving agent group is not swept, and the receipt says `stopped: true, residual_pids: []`. This fails toward leaving a process, never toward killing a foreign one. It applies only when the holder and the caller have different TZs **and** the agent started inside the one repeated hour per year of a DST zone that either of them uses. The default zone on this Mac (Asia/Shanghai) has no DST.
- Docs: docs/api.md:404-405 says "(epoch seconds, so time zones do not matter)". That is slightly too absolute.
- Possible fix, left to the implementer: the holder could record `start_tvsec` directly from libproc (`proc_pidinfo` PROC_PIDTBSDINFO) instead of going through text, and the CLI could read the leader's `start_tvsec` the same way when libproc is available. Otherwise, narrow the doc wording.

### I4 INFORMATIONAL. `checked` requires a numeric value, so interim-build string values are trusted
A record written by an 83052ce-build holder, where `agent_started` is a string, now takes the legacy trusted path (scripts/kaola-acp.py:1236-1237). Likewise, an 83052ce-build CLI reading a new record treats the float as unchecked, which also means trusted. Both directions fail toward the pre-#132 behavior, and neither build was released. I note this only for completeness.

## Brief question 3: regressions, and remaining medium or higher issues in 428e7bb..efc9c0c
I found no regression in the delta.
- The new L3 refusal also refuses a legacy record without `holder_instance_id` whose holder answers on the argv socket (`None != id`). `holder_instance_id` dates from #39, so this is not a realistic population. The derived-socket path for the same spelling does not go through this branch.
- The leader-absent branch still includes the group (scripts/kaola-acp.py:1271-1272).
- An unparseable leader `lstart` excludes the group, which fails toward not killing.
- A holder that cannot read its own `lstart` records `None`, which gives the legacy trusted path.

I found no remaining medium or higher defect. The host-exists, identity and stop paths were covered in earlier rounds and are unchanged here apart from the L3 guard.

## Commands run
- `git log --oneline 428e7bb..HEAD`; `git diff 83052ce efc9c0c --stat -- ':!skills' ':!hosts'`; `git diff 83052ce efc9c0c -- ':!skills' ':!hosts' ':!*.md'` and `-- docs`
- `grep`/`sed` reads of scripts/kaola-acp.py (answering_socket, holder_identity, force_stop_unreachable, recorded_groups) and scripts/kaola-acp-holder.py (start_epoch, process_table, libproc_ps strftime)
- `env $U STOPTZ=UTC python3 /tmp/rv132h/tz.py <wt>/scripts/kaola-acp.py /tmp/rv132h/repo`, plus the same with no STOPTZ and with `STOPTZ=America/New_York` (M2)
- `python3 /tmp/rv132h/dst.py` (round trip of ambiguous-hour text per TZ)
- `env $U TZ=UTC python3 /tmp/rv132h/dst2.py` and `env $U TZ=America/New_York python3 /tmp/rv132h/dst2.py` (L4 through `recorded_groups`)
- `env $U python3 /tmp/rv132h/foreign.py <wt>/scripts/kaola-acp.py /tmp/rv132h/repo` (L3)
- `env $U python3 tests/contract/test-acp-contract.py Issue132AnchorUnitTests Issue132HolderIdentityTests`: 16 tests OK
- `env $U TZ=America/New_York python3 tests/contract/test-acp-contract.py Issue132AnchorUnitTests`: 6 tests OK
- `env $U python3 scripts/render-skills.py --check`: PASS
- `git status --short` in the worktree was clean.
- Leak check: `pgrep -fl 'RVW-|rv132|sleep 300'` found nothing. Every holder, agent group and fake PID I started is gone. The five `kaola-acp-holder` processes that remain belong to other repos or installed Skill copies (vrpcadcore, kaola-workflow, the KPR orchestrator Host), existed before this review, and are not mine.
- I did not run scripts/validate.sh.

(`$U` is the brief's `KAOLA_*` scrub, which excludes `KAOLA_VALIDATE_*`.)
