# Codex user-level compact recovery — isolated live verification (Issue #97)

Date: 2026-09-19. Host: macOS arm64, codex-cli 0.153.4 for the first session,
0.155.1 for the rest (Codex self-updated when an Enter meant for the
directory-trust prompt landed on its update prompt; the update was allowed to
finish rather than interrupting a global npm install). Candidate under test:
branch `workflow/issue-97` at the commits recorded in `mission-list.md`.

Method: an isolated `CODEX_HOME` under the session scratchpad
(`codex-live/home`) with `auth.json` symlinked from the real Codex home (never
read, copied, or printed by this verification), no other real configuration.
Before installing, `hooks.json` was preset with the real Kaola Workflow user
entry (`kaola-workflow:compact-context`, pointing at the real Workflow payload
path) and a user-owned entry (`user-owned:startup-notes`). The real installer
then ran `--runtime codex --platform zcode --no-bin-links`
(`05-isolated-home-hooks-after-install.json`: the two foreign entries
unchanged, ours appended). Five scratch Git repositories (`repoA`…`repoE`),
unrelated to Runner, each held only a README and `calc.py`. Every session was a
real interactive `codex` in tmux; nothing was passed with
`--dangerously-bypass-hook-trust`. Zero writes to `~/.codex`. All tmux sessions
were exited with `/quit` (none remain).

## Trust flow (00–04, 20–21, 52, 55)

- First launch in a fresh home (0.153.4): after the directory-trust prompt,
  *"Hooks need review — 3 hooks are new or changed"* with *Review hooks / Trust
  all and continue / Continue without trusting (hooks won't run)* (`00`).
- `/hooks` browser: `SessionStart Installed 3 / Active 0 / Review 3` (`01`);
  the per-hook list shows Hook 3 = ours, *Source User config … hooks.json*,
  *Command python3 …/kaola-project-runner/hooks/kaola-codex-compact-hook.py
  user-emit*, *Trust New hook - review required* (`03`); `t` trusted each;
  afterwards `Installed 3 / Active 3` (`04`).
- The user-owned fixture entry originally ran `/bin/true`, which does not exist
  on this macOS (only `/usr/bin/true`), so it failed with exit 127 in session C
  (`10`, `11`) — a fixture defect, not ours. It was changed to `/usr/bin/true`
  before session A; the next launch flagged **only that modified hook**
  (`20`, `21`: `[x] Hook 1 / [!] Hook 2 · modified / [x] Hook 3`), ours stayed
  trusted. Trust persisted across all later sessions.
- Session E's repository additionally carried the legacy project-level entry
  (`50`, `51`): its launch flagged *1 hook is new or changed* (the project
  entry), trusted, `/hooks` then showed `SessionStart Installed 4 / Active 4`
  (`52`, `55`).

## Session C — ordinary session, repoC (0.153.4; `10`–`12`)

Prompt `READY`, real `/compact` (rollout `compacted` at ordinal 20), probe.
Rollout: two developer `additionalContext` messages after the compaction
(33 `KW-COMPACT-RECOVERY`, 34 `KPR-USER-COMPACT-RECOVERY`), no tool calls.
Final answer: quotes both markers and states *No Skill file was read, no
delegation or Host was started, and no other action was taken because of
them.* → the conditional payload reaches an ordinary session and it does not
start project work.

## Session A — outer Delegator, repoA (0.155.1; `22`–`24`)

Turn 1 used `$kaola-delegator` read-only (real `cat` of the installed
`home/skills/kaola-delegator/SKILL.md` + `references/handoff.md`, ordinals
15–17). Real `/compact` (30). After it: 43 `KW-COMPACT-RECOVERY`, 44
`KPR-USER-COMPACT-RECOVERY`, then on the probe turn a real `CommandExecution`
`cat …/home/skills/kaola-delegator/SKILL.md` (51–52) — the model re-read the
installed Delegator Skill because of the hook — and the final answer (59)
quotes the four marker lines, names that path as re-read, and states *I did
not start, resume, send to, or contact any Host.*

## Session B — outer Delegator, repoB (0.155.1; `30`, `34`)

Same scenario in a second unrelated repository. Compaction at 31; 44
`KW-COMPACT-RECOVERY`, 45 `KPR-USER-COMPACT-RECOVERY`; probe turn re-listed and
re-read the installed Skill directory (52–54, `SKILL.md` and
`references/handoff.md`); final answer (60) quotes both markers, lists both
installed paths as re-read, *I started no Host and contacted no Host.*
(During this run the `/compact` slash-command popup swallowed the first Enter;
a second Enter was sent by the operator — a driver artefact, not a hook fact.)

## Session D — Project Runner, repoD (0.155.1; `40`, `44`)

Turn 1 used `$kaola-project-runner` read-only (`rg` on the installed
`SKILL.md`, 15–16). Compaction at 30; 43 `KW-COMPACT-RECOVERY`, 44
`KPR-USER-COMPACT-RECOVERY`; probe turn: real `CommandExecution`
`cat …/home/skills/kaola-project-runner/SKILL.md` (51–52) and the pane shows
*I'm re-reading the installed Project Runner Skill required by the recovery
hook* and *Explored — Read SKILL.md (kaola-project-runner skill)*. The
operator's `/quit` arrived while the answer was still being produced, so the
rollout ends with `turn_aborted` (ordinal 60) and holds no final answer for the
probe. The re-read itself — the model-reading evidence — is in the rollout;
the self-report is only in the pane capture (`40-…-probe.txt`).

## Session E — legacy project-level entry bound, repoE (0.155.1; `50`–`58`)

`prepare` ran before launch (`50`, inert binding). After turn 1 the session id
was taken from the rollout's `session_meta` and bound (`53`, id masked;
`54`: `bound: true`). Real `/compact` (30). After it the rollout holds exactly
two developer messages: 43 `KW-COMPACT-RECOVERY` and 44
**`KPR-COMPACT-RECOVERY`** (the project block) — **no `KPR-USER-…` block**:
`user-emit` yielded to the bound project entry, so one compaction carried one
Runner block and none was lost. Final answer (50): quotes
`KW-COMPACT-RECOVERY-V2` and `KPR-COMPACT-RECOVERY-V1`, *took no
project-level action*, *Files read after compaction: none*, *Worker or Host
started: no*. (The project payload's own reload behaviour is the Issue #75
carrier, unchanged here.)

## Boundaries

- Live proof covers: the user entry is trusted through the normal `/hooks`
  flow (not bypass), fires on real `/compact` from any repository, is acted on
  by sessions already using the Delegator or Project Runner Skill (real
  re-read of the installed `SKILL.md`), is ignored by an ordinary session, and
  defers to a bound legacy project entry.
- Not staged live: an automatic (mid-turn) compaction; the documented Codex
  behaviour is the same `SessionStart(compact)` path. The unbound and
  other-repository directions of the deferral predicate are proven by the
  contract suite (`tests/contract/test-issue-97-codex-user-compact-hook.py`).
- Model quota on the account was below 10 % of the weekly limit during the run;
  every session switched to `gpt-5.6-luna` when Codex offered it. No session
  was re-run to improve a self-report.
