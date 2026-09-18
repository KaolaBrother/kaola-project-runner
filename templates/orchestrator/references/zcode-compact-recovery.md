# ZCode Host compact recovery (Issue #75)

Read this when a bound ZCode Host's own context was compacted mid-run and the
next `send` must restore its footing. ZCode 0.16.5 has no compact hook —
`SessionStart` fires on `startup`/`resume` only, the hook event enum has no
compact event, and nothing about compaction surfaces through the ACP stream
(`observe`/`capture` show none, `context_usage` stays null). Recovery rides
your next prompt; the runtime cannot inject it.

Verified live on ZCode 3.12.3 / CLI 0.16.5: a prompt whose text is `/compact`
runs a real manual compaction (persisted as `compaction` /
`context_compaction` `part`-table rows, `trigger:"manual"`), and the next
prompt carrying the carrier below made the model execute a real read of the
installed Skill and quote the reload marker planted in its payload.

## When to send the carrier

- After **your own** `/compact` to the Host — the common case, self-evident
  because you asked for it.
- After a compaction confirmed another way. Auto-compaction exists but is
  silent in the ACP stream. A read-only `part`-table query against the
  runtime's `db.sqlite` (rows with `type='compaction'` or
  `timelineType='context_compaction'`, newest `time_created`) is a diagnostic
  you may run when you need the fact — never a per-send check, never a
  transport gate, never a cursor ledger.
- Once per compaction episode, at the head of the next prompt only. If the
  reply does not prove the reload, send it once more — never on every send.

## The carrier

Put this text at the head of the next prompt to the compacted Host, with the
Skill path actually installed:

```text
Recovery marker: KPR-ZCODE-RECOVERY-V1. You are a ZCode host Agent running
Project Runner. After context compaction, completely re-read the installed
Skill at <installed kaola-project-runner SKILL.md path>, then recover the
live scene from current authorization, the effective-now heartbeat, and the
run records — never re-intake, re-claim, restart sessions, or re-dispatch
in-flight work. Reply with the reload marker inside the Skill's
references/zcode-compact-recovery.md to prove the read.
```

Skill reload marker: `KPR-SKILL-RELOAD-V1`. It lives only inside this file in
the installed Skill payload, so a reply quoting it proves a real read, not a
memory answer; the verification experiment used `KPR-SKILL-RELOAD-7931` the
same way. For a stronger check, also ask for a detail only the re-read Skill
states and verify it yourself.

## Boundaries

No ZCode config or hook file is touched (user `cli/config.json` keeps its own
state), nothing installs or uninstalls, the transport stays transport-only,
and no scheduler, ledger, or send-path database check is added.
`UserPromptSubmit` could carry recovery too — wider prompt coverage, but it
costs a user-global `hooks.enabled` write plus a process per prompt for
coverage the Runner does not need; it stays the documented fallback, not the
mechanism. Unverified: auto-compaction exercised live (same record family per
static analysis), and carrier behavior on prompts composed outside the
Runner.
