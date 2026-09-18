# ZCode Host compact recovery (Issue #75)

Read this when a bound ZCode Host's own context was compacted mid-run and its
footing must be restored. ZCode 0.16.5 has no compact hook — `SessionStart`
fires on `startup`/`resume` only, the hook event enum has no compact event,
and nothing about compaction surfaces through the ACP stream
(`observe`/`capture` show none, `context_usage` stays null).

## Two carriers, and only one is durable

Live experiments on installed ZCode 3.12.3 / CLI 0.16.5 established exactly
one **durable** carrier — one that survives compaction by construction
instead of depending on a later `send`:

- **Durable: an owner-authorized `AGENTS.md` standing instruction**, present
  in the consuming project's workspace file *before the Host session
  starts*. The runtime resolves workspace `AGENTS.md` once per session into
  the per-request context prefix — outside the history compaction rewrites —
  so the instruction reaches the first inference after **any** compaction,
  manual or automatic, with no send, hook, or detection at all. This is the
  only carrier verified through a real `trigger:"auto"` compaction.
- **Per-send: the prompt carrier below.** It restores a Host after a
  compaction you know about — your own `/compact`, or one confirmed from
  `part` records. It cannot prove the automatic same-turn case by itself:
  it rides a prompt someone chooses to send, and nothing guarantees one
  lands before the Host's next inference.

The per-send carrier stays shipped because it needs no project file and no
owner step; the durable block is the verified answer for automatic
compaction and is adopted only by explicit project-owner choice — the Runner
never writes a consuming project's `AGENTS.md` itself.

## The durable carrier — reusable block

Owner-authorized, placed in the consuming project's `AGENTS.md` (or
`.zcode/AGENTS.md`) before the Host session starts. Every Agent in the
workspace reads that file, so the block is explicitly role-scoped: it
applies only to the designated Host — one project has only one Runner
Agent — and ordinary Workers pass over it. Fill in only the Skill path —
the installed payload actually in use (`kaola-project-runner` or
`kaola-delegator`). There is no fixed cross-project marker or schema to
adopt; the proof marker stays inside the Skill payload itself.

```text
## Compact recovery (designated Project Runner Host only)

This block applies only if you are the Agent designated as this project's
ZCode Project Runner Host, or an outer host genuinely running
kaola-delegator. Ordinary Workers and single-issue Workflow Agents ignore
it entirely — it never makes a worker into a runner.

Your Host work is driven by the installed Skill at
<installed SKILL.md path>. If your context was compacted and that Skill's
full text is no longer present, completely re-read the file before any
runner work, then recover the live scene from current authorization, the
effective-now heartbeat, and existing run and in-flight records — never
re-intake, re-claim, restart sessions, or re-dispatch in-flight work.
Prove the re-read by quoting the reload marker inside that Skill's
references/zcode-compact-recovery.md.
```

Recovery semantics are the same as for the per-send carrier: re-read the
Skill in use, then continue the same frontier from effective authorization,
the live heartbeat body, and existing records. The block never dispatches
work and never makes decisions — it only restores footing.

## When the per-send carrier applies

- After **your own** `/compact` to the Host — the common case, self-evident
  because you asked for it.
- After a compaction confirmed another way. Auto-compaction exists and is
  silent in the ACP stream; a read-only `part`-table query against the
  runtime's `db.sqlite` (rows with `type='compaction'` or
  `timelineType='context_compaction'`, newest `time_created`) is a
  diagnostic you may run when you need the fact — never a per-send check, never a
  transport gate, never a cursor ledger.
- Once per compaction episode, at the head of the next prompt only. If the
  reply does not prove the reload, send it once more — never on every send.

## The per-send carrier

Put this text at the head of the next prompt to the compacted **Host** — the
designated ZCode Project Runner session only, never an ordinary Worker —
with the Skill path actually installed:

```text
Recovery marker: KPR-ZCODE-RECOVERY-V1. You are the designated ZCode Project
Runner Host. After context compaction, completely re-read the installed
Skill at <installed kaola-project-runner SKILL.md path>, then recover the
live scene from current authorization, the effective-now heartbeat, and the
run records — never re-intake, re-claim, restart sessions, or re-dispatch
in-flight work. Reply with the reload marker inside the Skill's
references/zcode-compact-recovery.md to prove the read.
```

Skill reload marker: `KPR-SKILL-RELOAD-V1`. It lives only inside this file
in the installed Skill payload, so a reply quoting it proves a real read,
not a memory answer; the verification experiments used
`KPR-SKILL-RELOAD-7931` and `KPR-SKILL-RELOAD-8842` the same way. For a
stronger check, also ask for a detail only the re-read Skill states and
verify it yourself.

## Evidence and boundaries

Verified live (installed ZCode 3.12.3, unpatched):

- Manual `/compact` → per-send carrier → real `read` of the installed Skill
  → reload marker quoted, on a real GLM model.
- Manual `/compact` → durable AGENTS block → real `read` driven by the
  standing instruction alone (no carrier in the prompt), real GLM model.
- Real `trigger:"auto"` compactions (`context_limit`, `pre_request`,
  `status:"completed"`) on an isolated declared-window MOCK provider → the
  request immediately following each compaction still carried the
  `# agentsMd` section and the standing instruction — prefix survival
  observed on the wire.

Not verified: real GLM model *behavior* after an actual auto-compaction
(the installed catalog models are 1M-window; auto-compaction on a real GLM
account is beyond bounded cost), and carrier behavior on prompts composed
outside the Runner.

Boundaries: the Runner never writes a consuming project's `AGENTS.md`
itself — the durable block exists only where the project owner explicitly
authorized it. No ZCode config or hook file is touched (user
`cli/config.json` keeps its own state), nothing installs or uninstalls, no
global hook is added, the transport stays transport-only, and no scheduler,
ledger, polling loop, or send-path gate is added. `UserPromptSubmit` could
carry recovery too — wider prompt coverage, live-verified in isolated
scope — but it costs a process per prompt for coverage the durable block
already gives; it stays the documented fallback, not the mechanism.
