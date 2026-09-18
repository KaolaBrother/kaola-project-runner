---
name: kaola-delegator
description: "Use when an outer Agent (Grok Bot, Codex, or generic) should delegate a project run through Kaola-Delegator to one ZCode Host: extract the task, progress, authorized platforms/quota/priority, and project context, start or resume that Host via the ZCode Runner, and relay user changes without dispatching workers."
---

# Kaola-Delegator

This Skill is the external delegation Skill. It is not Project Runner and not a
platform worker. Shared core for Grok Bot (after the account bridge), Codex, and
generic Skill-directory hosts.

Project Runner (`kaola-project-runner`) is the inner control-plane Skill. A
ZCode Host loads it and owns planning, worker dispatch, notification binding,
path binding, heartbeat, acceptance, and Workflow close-out. Do not copy that
engine.

## Extract once

From the user and existing records collect only: goal; already-done and remaining
work; authorized worker platforms and counts; quota as separate concurrency,
account, and token figures; priority; delivery and stop boundary; the explicit
project path and authorization already given. Ask only for a missing or
conflicting item that blocks the one handoff. Do not invent platforms, fuse
quota units, raise quota, or expand authorization.

## One Host

Use the installed ZCode Runner (`zcode-kaola-project-runner`) to start or resume **one**
exact ZCode Host. An existing Host for this work is resumed, never duplicated.
Do not rename, restart, or cancel in-flight Hosts to adopt this Skill.

Hand over in one non-blocking `send --no-wait` only: the extracted task and
progress; authorized platforms, quota, and priority; project context as given;
the Host identity it cannot discover (`platform`/`session`/`repo`); and that it
must load `kaola-project-runner` and finish the run internally. Do not pass
per-worker notification bindings, per-worker `--repo`, scheduling, or heartbeat
instructions. Commands and the prompt fields:
[handoff.md](references/handoff.md).

## After the handoff

Relay later user changes to that same Host. Read delivery through the Host's
replies. Escalate only an unrecoverable exception that needs a human decision,
and keep it in this conversation. Do not dispatch workers, copy a Mission List,
maintain a heartbeat, create a Routine, or operate on inner sessions.
