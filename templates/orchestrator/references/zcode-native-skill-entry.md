# ZCode Host: the native Skill entry (Issue #94)

Read this for how the designated ZCode Host loads — and reloads — the Project
Runner Skill: first startup, resume or live attach, a new Host continuing the
run, every worker-event heartbeat, and the round after any context
compaction. One mechanism covers all five. No `AGENTS.md` block, no
role-scoping judgement, no compaction detection, and no manual `read` of a
`SKILL.md` file is involved anywhere.

## The one entry

Every prompt that opens a Host turn — an idle `send`, the first handoff, a
resume or attach update, a worker-event notification, and the round after
any compaction — **opens with the native Skill command
`/kaola-project-runner` on its own first line**, followed by that prompt's
own content. ZCode keeps each enabled Skill's metadata (name and
description) visible to the model in every request — injected per request
alongside the `AGENTS.md` prefix, outside the history compaction rewrites —
and its runtime instructs the model that `/<skill-name>` is invoked through
the Skill tool. A prompt opening with the command therefore produces a
native `Skill` tool_call that loads the body, and the rest of the prompt is
handled normally. Re-invocation while the body is already loaded is a cheap
idempotent repeat, so the same head is right whether or not the last turn's
context survived.

Where each entry point gets the line:

- **Startup and new Host** — the outer Agent's first handoff opens with
  `/kaola-project-runner`, then the Host role, identity and authorization
  fields (see `references/handoff.md` in `kaola-delegator`).
- **Resume and live attach** — the continuation prompt after
  `start --resume`, or the update `send` to an attached live Host,
  opens the same way. Resumed history may still carry the body; the
  re-invocation is harmless.
- **Worker-event heartbeat** — the host holder's notification prompt
  carries the command as its first line, before the `kaola-host-notify/1`
  block. The Host writes no command into `heartbeat-prompt.json` itself;
  the envelope owns the entry.
- **After a known compaction** — nothing extra. The next prompt, whatever
  it is, already opens with the command, so the Skill body reloads through
  the same native channel. There is no carrier text to compose, no
  detection step, and no "reload now" instruction — a compacted Host is
  indistinguishable from any other Host at the prompt boundary.
- **Busy `steer`** — not a prompt, and not an entry. A mid-turn steer
  forwards its guide text into the already-running turn verbatim; the turn
  keeps the Skill body it loaded at its own first line, so no new `Skill`
  tool_call is produced, needed, or promised. A fresh invocation is only
  meaningful at a turn boundary — end the turn and use an ordinary prompt.

## Discovery precondition

Native invocation needs the generated `kaola-project-runner` Skill installed
where the Host session discovers skills. Verified against the installed
ZCode 3.12.3 — in its `createSkillsService` binary code and live through
injected skill metadata — the install-relevant roots are the workspace
`<repo>/.zcode/skills/` and `<repo>/.agents/skills/`, the user-level
`~/.zcode/skills/` and `~/.agents/skills/`, plus the same two roots on each
ancestor directory up to the workspace boundary (plugin cache roots are a
separate mechanism, not an install target). `--runtime zcode` installs to
`~/.zcode/skills/`; `--skills-dir` accepts any of these, e.g.
`<repo>/.agents/skills`. A `--skills-dir` outside the discovered roots
still works for an agent that reads the file itself — but a ZCode Host does
not read the file. If the first beat's `capture` shows no `Skill` tool_call,
the Skill is not installed where this session discovers it: report that
fact and install it properly; do not fall back to reading `SKILL.md` by
hand.

## Facts that did not change

- ZCode 0.16.5/3.12.3 has no compaction hook (`SessionStart` fires on
  `startup`/`resume` only) and surfaces no compaction through ACP:
  `observe`/`capture` show none and `context_usage` stays null.
- `/compact` and the `session/compact` RPC write the same `compaction` /
  `context_compaction` `part` rows in `db.sqlite`. A read-only cursor on
  that table remains an optional diagnostic for a compaction you did not
  order — never a per-send check, a transport gate, or a ledger.
- Auto-compaction is real and equally silent; completed episodes carry
  `trigger:"auto"` on the same rows.
- Workspace `AGENTS.md` content is still resolved into the per-request
  prefix and still survives compaction — a true runtime fact, now only
  background. The Runner plants no block and writes no consuming project
  file; ordinary Agents in the same repo carry no Host instruction at all.

## Evidence and boundaries

Verified live (installed ZCode 3.12.3, repo adapter 0.3.3):

- Real GLM model: `/kaola-project-runner` produces a native `Skill`
  tool_call; a manual `/compact` then `/kaola-project-runner` produces a
  **new** `Skill` tool_call returning a Skill-body marker — not a manual
  `read` (Issue #94 matrix, 2026-09-19).
- Command plus trailing prompt text: the `Skill` tool_call fires and the
  rest of the prompt is handled normally — the form the heartbeat envelope
  uses.
- Real `trigger:"auto"` compactions (isolated mock provider, declared small
  `contextWindow`, scratch `HOME`): the request after each completed
  compaction still carries the `/<skill-name>` invocation rule and the
  `kaola-project-runner` skill metadata on the wire.
- Discovery roots (Issue #94 review fix): the installed 3.12.3 binary
  resolves workspace `.zcode/skills` and `.agents/skills`, user
  `~/.zcode/skills` and `~/.agents/skills`, plus both roots on ancestor
  directories; a scratch-HOME live probe injected the
  `kaola-project-runner` metadata from each `.agents/skills` root.

Not verified: real-model *behaviour* after a genuine auto-compaction — the
catalog GLM models are 1M-window and forcing one is beyond bounded cost —
any compact-specific ACP event, because none exists, and a `Skill`
tool_call from a busy `steer` guide, because steer forwards the guide into
the running turn and no re-invocation is claimed. The pre-0.3.3
installed adapter exits against ZCode 3.12.3; update the install rather
than the mechanism.

Boundaries: no project `AGENTS.md` block, and no hook, plugin, command
registry, scheduler, polling loop, cursor ledger, or state machine added
anywhere. The only transport change is the one envelope line, and ordinary
Workers see none of this.
