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
own content. ZCode keeps each enabled Skill's metadata visible to the model
in every request — injected alongside the `AGENTS.md` prefix, outside the
history compaction rewrites — and instructs it to invoke `/<skill-name>`
through the Skill tool. A prompt opening with the command therefore produces
a native `Skill` tool_call that loads the body, and the rest of the prompt
is handled normally. Re-invocation while the body is loaded is a cheap
idempotent repeat — right whether or not the last turn's context survived.

Where each entry point gets the line:

- **Startup and new Host** — the outer Agent's first handoff opens with
  `/kaola-project-runner`, then the Host role, identity and authorization
  fields (see `references/handoff.md` in `kaola-delegator`).
- **Resume and live attach** — the continuation prompt after
  `start --resume`, or the update `send` to an attached live Host,
  opens the same way. Resumed history may still carry the body;
  re-invocation is harmless.
- **Worker-event heartbeat** — the host holder's notification prompt
  carries the command as its first line, before the `kaola-host-notify/1`
  block. The Host writes no command into `heartbeat-prompt.json` itself;
  the envelope owns the entry.
- **After a known compaction** — nothing extra. The next prompt, whatever
  it is, already opens with the command, so the Skill body reloads through
  the same native channel — no carrier text, no detection step, no
  "reload now" instruction. A compacted Host is indistinguishable from
  any other Host at the prompt boundary.
- **Busy `steer`** — not a prompt, and not an entry. A mid-turn steer
  forwards its guide text into the already-running turn verbatim; the turn
  keeps the Skill body it loaded at its own first line, so no new `Skill`
  tool_call is produced, needed, or promised.
- **Composite `steer --steer-mode interrupt`** — its resend *is* a
  turn-opening prompt, but the composite path is **not** a Host recovery
  entry. It cancels the running turn, confirms it stopped, then sends the
  steering text once, verbatim, as the next turn; the holder never
  infers Host identity from prompt content and never adds the command
  itself. Do not use it to open a Host round unless the caller supplies
  `/kaola-project-runner` as the steering text's own first line, which
  the resend then carries unchanged. For mid-turn steering, native
  `steer` above is the supported path.

## Discovery precondition

Native invocation needs the generated `kaola-project-runner` Skill installed
where the Host session discovers skills. ZCode's install-relevant **default**
roots are the workspace `<repo>/.zcode/skills/` and `<repo>/.agents/skills/`,
the user-level `~/.zcode/skills/` and `~/.agents/skills/`, plus the same two
roots on each ancestor directory up to the workspace boundary. The defaults
are not the whole discovery surface: `skills.roots` in
`~/.zcode/cli/config.json` adds configured skill roots scanned as
project-scope roots; `plugins.dirs` in the same file adds plugin roots whose
`skills/` are scanned too (a plugin skill surfaces namespaced as
`<plugin>:<skill>` and stays loadable by its plain name); plugin cache roots
remain a separate mechanism, not an install target.
`--runtime zcode` installs to `~/.zcode/skills/`; `--skills-dir` accepts
any of these roots, e.g. `<repo>/.agents/skills`. A `--skills-dir` outside
every discovered root — default or configured — still works for an agent
that reads the file itself, but a ZCode Host does not read the file: the
first line then arrives as plain text. If the first beat's `capture` shows
no `Skill` tool_call, the Skill is not installed where this session
discovers it: report that fact and install it properly; do not fall back
to reading `SKILL.md` by hand. Measured versions, the compaction facts and
the live evidence: `docs/host-entry-evidence.md` in the Project Runner
checkout.

Boundaries: no project `AGENTS.md` block, and no hook, plugin, command
registry, scheduler, polling loop, role classifier, session marker,
cursor ledger, or state machine added anywhere. The only transport
change is the one envelope line, and ordinary Workers see none of this.
