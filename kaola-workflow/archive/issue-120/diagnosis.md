# #120 diagnosis — dsh worker inside a dsh Host

Measured 2026-09-22 on dsh 0.1.5-rc.2, worktree `workflow/issue-120` (base fd909e1). Temp HOME
`/tmp/kpr120/home`, isolated `KAOLA_ACP_RECORD_ROOT=/tmp/kpr120/records`, DSH_HOME copies only
(`/tmp/kpr120/home/.dsh`, `/Volumes/WorkspaceA/ylminiserver/workspace/kpr120-scratch/.dsh`); real
`~/.dsh` read-only (rsync source; mtimes diffed unchanged).

## Root cause (one cause, two effects)

dsh's `acp` bundle composes `sandbox-policy.mode = process.env.DSH_PERMISSION_MODE ?? 'workspace-write'`
and wraps every model shell command in macOS Seatbelt (`sandbox-exec -p "(allow default)(deny
file-write*)(allow file-write* <workspace> /tmp $TMPDIR)"`). Seatbelt is kernel-enforced and inherited
by every descendant; `start_new_session` / setsid does not leave it. So a Runner `start` run from a dsh
Host's shell tool spawns a holder and agent that are confined too.

1. **Start**: `dsh --profile acp` boot (`profile-boot prepareProfile`) unconditionally rewrites
   `$DSH_HOME/profiles/acp/cordis.yml`. With a normal `~/.dsh` that is outside the writable roots →
   `EPERM` → node exits 1 before any stdout → holder `acp-initialize-failed / agent-exited`, exactly the
   #119 receipt. The EPERM stack was only in the record's `stderr.log`; the receipt carried no cause.
   (#119 grok `session/new` EPERM = same class: a worker writing its own home.)
2. **Stop**: setuid `/bin/ps` cannot exec under any Seatbelt profile (`execvp ... Operation not
   permitted`). The holder's `_terminate_group` → `process_table`/`group_members` raised, the op thread
   died, the client got `holder-closed`, and the worker holder leaked in `stopping`. #119's dsh-row
   claude-code worker shows the same (`state: stopping` after the Host's stop; masked because the agent
   had already exited 0 on stdin close).

Not the cause: DSH_SESSION_ID / DSH_SHELL / DSH_HOME injection (initialize rc=0 with each), same-platform
nesting as such (leg B: dsh-in-dsh ready when unconfined).

## Evidence (`evidence/`)

- `probe.sh` — run by the Host's own shell tool: `sandbox_check`, `/bin/ps`, env, worker start/stop.
- Leg A (default mode, DSH_HOME outside writable roots): `A-probe.out` — `sandbox_check=1`, `ps rc=126`,
  worker `state: error`, `acp-initialize-failed`, now with `seatbelt_confined: true` + `stderr_tail`
  naming `EPERM ... kpr120-scratch/.dsh/profiles/acp/cordis.yml`; worker stop `holder-closed` (pre-shim).
- Leg B (`DSH_PERMISSION_MODE=danger-full-access` on the Host): `B-probe.out` — `sandbox_check=0`,
  `ps rc=0`, worker `state: ready`, worker stop `stopped: true, residual_pids: []`.
- Standalone: `sandbox-exec` + dsh's exact SBPL around `dsh --profile acp` initialize → same EPERM, rc 1.

## cc-in-cc

This session is a claude-code worker (CLAUDECODE=1, CLAUDE_CODE_ENTRYPOINT=sdk-cli) with
`sandbox_check=0`, so the cc-in-cc initialize exit 1 is not this Seatbelt class. Not reproduced here
(a live Claude start writes real `~/.claude`); left as a follow-up.
