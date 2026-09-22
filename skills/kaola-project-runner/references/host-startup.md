# Startup: ordinary worker flow, and the Host's own startup receipt

Read this for ordinary worker supervision from Project Runner, or when this
session **is** the ZCode Host doing its own startup. Outer Agents start or
continue that Host through Kaola-Delegator (`kaola-delegator`); that Skill is
the single source for outer recover/start/send/stop. Every command here is the
installed form; no platform argument, no new tool.

```bash
SKILLS="<skills root>"   # the root your own runtime installed to, e.g. $HOME/.zcode/skills
WORKER="$SKILLS/codex-kaola-project-runner/scripts/runtime-tmux.sh"
HOSTRUN="$HOME/.zcode/skills/zcode-kaola-project-runner/scripts/runtime-tmux.sh"
PROJECT="/abs/path/to/project"     # the consuming project's canonical Git root
```

## A. Ordinary worker supervision

You keep authorization, dispatch, acceptance and close-out in your own session.
Nothing below in this file applies: no event binding, no heartbeat file, no Host.

```bash
"$WORKER" start   --repo "$PROJECT" --session codex-KT-i274-parser
"$WORKER" send    --repo "$PROJECT" --session codex-KT-i274-parser --text '<the task>'
"$WORKER" observe --repo "$PROJECT" --session codex-KT-i274-parser
"$WORKER" capture --repo "$PROJECT" --session codex-KT-i274-parser --lines 200
"$WORKER" stop    --repo "$PROJECT" --session codex-KT-i274-parser
```

That one exact name is the issue-scoped dispatch name of
[issue-dispatch.md](issue-dispatch.md): the platform id, the consuming project's declared
heartbeat short code, `i` plus the real issue number, and a purpose token. All five
operations use it unchanged.

Check each receipt: a `start` without a ready session started nothing, a `send`
`error` dispatched nothing, and a `prompt_timeout` or missing receipt leaves
consumption **unknown** — `observe` establishes the fact before anything is
re-sent. Blocking `send` is a normal, supported way to wait here.

## B. Outer Agent: starting a Host

Do not start the Host from this file. Follow Kaola-Delegator (`kaola-delegator`)
and its `references/handoff.md`. This section exists only so a Host that loaded
this Skill does not copy a second outer procedure. Exceptions reach you; worker
handling does not. Do not take that over session by session.

   Every turn-opening prompt to the Host — the first handoff, a resume or
   attach update, a worker-event notification, and the round after any
   compaction — opens with `/kaola-project-runner` as its first line (a
   non-ZCode Host: its platform's `host_skill_entry`, per
   [host-entry-matrix.md](host-entry-matrix.md); an empty entry cannot host
   and refuses `host-entry-unsupported`). A busy
   `steer` guide is not a new prompt: it enters the running turn verbatim,
   keeps the already-loaded context, and is no new Skill invocation. The
   composite `steer --steer-mode interrupt` ends the turn and resends on a
   new one verbatim — not a Host recovery entry; supply the first line
   yourself if a resend must open a Host round. That
   native invocation is the whole recovery mechanism; no `AGENTS.md` block,
   role check, or compact detection is involved. Facts and boundaries:
   [zcode-native-skill-entry.md](zcode-native-skill-entry.md).

## C. The Host's own startup and beat

The prompt that woke you already loaded the main Skill through its first-line
entry (`/kaola-project-runner` on ZCode) — startup, resume and post-compaction rounds
alike; never `read` a `SKILL.md` path by hand. Read the plan and the project's
recovery records, and answer
with a short startup receipt: role, authorization (platforms, count, implement or
supervise-only), lifecycle target and stop boundary, where those facts came from,
and every unresolved conflict. Then,
**before the first dispatch**, write the working heartbeat prompt to
`<project>/.kaola/heartbeat-prompt.json` as JSON with a non-empty string field
named exactly `body` (see `references/heartbeat-skeleton.md`). Any other field
name leaves the delivered notification carrying a reported defect instead of your
prompt — read that line in the notification and fix the file.

Where a session's native id comes from differs by platform, and `--resume` is
only honest with a verified one. ZCode reports its `sess_…` in that session's own
`native_session_identity` event - readable with `capture` - and only once the
session has run a turn; a freshly created one carries the bridge `zcode-N` id in
`session_meta` and no native id at all. Other platforms may publish theirs in
`session_meta`. No verified id means no `--resume`: start the session without
history and say so, rather than passing `acp_session_id` or `--continue`.

A Host `start` refuses `worker-skill-build-skew` (exit 1, nothing created) when
the installed worker Skills are a different build from the Skill this Host runs:
their `start` would be the copy without automatic binding. Nothing is recoverable
from inside the Host — report it with the `worker_skill_skew` paths and ask for
the install to be refreshed from the accepted checkout. `main-skill-build-skew`
is the same for an older copy of this Skill in a root the Host reads
(`main_skill_skew` paths): that copy may be the one loaded instead of this build.

The same `start` pinned this Host's model (Issue #108): a
`zcode-<PROJECT_CODE>-orchestrator-<purpose>` session must run GLM 5.3 at effort
`max`, applied then verified against the holder's advertised config and reported
in the receipt's `host_selection`. A `host-model-mismatch` /
`host-model-unverified` refusal is the outer Agent's evidence — a Host reading
this was verified before it ran.

The beat itself - starting workers from this session, non-blocking dispatch,
the `dispatch_event_cursor` reading anchor, ending
the turn as the wait, and reading the worker's real reply when an event wakes you
- is one procedure, written once in
[zcode-host-dispatch.md](zcode-host-dispatch.md). Follow it from there rather
than from a second copy.

## D. Which record holds what

| Record | Holds |
|---|---|
| Project Plan / authorized task plan | roles, authorization, lifecycle and stop boundary |
| Workflow mission ledger `kaola-workflow/.ledger/issue-<N>.jsonl` | engineering progress per run; Workflow writes, the Runner only reads |
| `.kaola/heartbeat-prompt.json` `body` | current identity, binding, run paths, next step |
| Runner receipts and holder events | what actually happened |

Keep them separate: no second plan is generated, no project history is rewritten,
and the heartbeat body is not a copy of the ledger. A `done`/`todo`
contradiction goes back to the record's owner; the Runner never rules work
complete. Report which main-Skill payload was loaded when a candidate checkout
and an installed release both exist.
