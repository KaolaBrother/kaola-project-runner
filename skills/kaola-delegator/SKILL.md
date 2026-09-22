---
name: kaola-delegator
description: "Use when an outer Agent (Grok Bot, Codex, or generic) should delegate a project run through Kaola-Delegator to one ZCode Host: extract the task, progress, authorized platforms/quota/priority, and project context, start or resume that Host via the ZCode Runner, and relay user changes without dispatching workers."
---

# Kaola-Delegator

This Skill is the external delegation Skill for Grok Bot (after the account
bridge), Codex, and generic hosts — not Project Runner, not a platform worker.

Project Runner (`kaola-project-runner`) is the inner control-plane Skill. A
ZCode Host loads it and owns planning, worker dispatch, path binding,
heartbeat, acceptance, and Workflow close-out. Do not copy that
engine. One project has only one Agent running Project Runner.

## Extract once

From the user and existing Git, Workflow, Issue, and Runner records collect:
goal; already-done and remaining work; authorized worker platforms/members and
counts and concurrency; the quota the user actually gave, each figure in its own
unit; priority; delivery and stop boundary; the explicit project path. On a
**live** Host, apply only the user's latest change — do not re-ask the full
set. On a **new** Host, missing, conflicting, or expired key values must be
confirmed before `start`. A quota unit the user never gave is not a missing key
value — carry it as unspecified and start; a quota whose unit is unclear is, so
ask. Do not open a blank Host. Do not invent platforms, fuse quota units, raise
quota, treat an unspecified quota as unlimited, reuse a stale quota, or expand
authorization.

## One Host

If the installed ZCode Runner (`zcode-kaola-project-runner`) is missing, report
that this Skill is not executable; claim no Host.

Recover from the canonical Git root plus the standard Host name
`zcode-<PROJECT_CODE>-orchestrator-<purpose>` and existing Runner `status` /
receipts. A Git worktree is not an ACP id. One live Host per repo: a **live**
Host is attached in place — do not `start` again, even if its recorded name is
not the new form, when that locator is unique. `host-exists` means attach its
`existing_host`; never rename and retry. A missing standard name or pointer
file never justifies a second Host. There is no Delegator continuation file.
A Host failing its identity check is exact-stopped, proven gone (`residual_pids: []`), then replaced. A **stopped** Host may
`--resume` an attested native
`sess_*`; if the backend cannot restore it, a **new** standard-named Host is
a new ACP session — confirm current authorization first, then start, and
continue the frontier from existing project records.
[Bricked Host](references/host-brick.md). Loaded from the Grok Bot
account bridge: before each Host `status`, `start` (also `--resume`),
`send`, and `stop`, attest with the existing locator's
full parameters (`--project`, `--worker zcode`, exact `--session`) and refuse
`refused`. Codex and generic hosts do not. Commands, identities, the
prompt's `sweep=` line: [handoff.md](references/handoff.md).

Pass no per-worker `--repo`, scheduling, or heartbeat instructions. Do not
rename, restart, or cancel an in-flight Host.
Exact Host `stop` and live attach use `holder_instance_id` from the existing
receipt (`--expected-holder-instance-id`); a different holder is not that Host.

## After the handoff

Relay later user changes to that same Host using idle `send` or, when busy, the
Runner's existing `steer` / a held undelivered update. A `--no-wait` admission or
a Host `end_turn` is not project delivery. After the first Host beat, check
file-read or work-product evidence and the first dispatch receipt against the
plan and authorization; do not trust the Host's self-description. Mismatch:
correct on this Host; do not accept completion. Read results with `observe` /
`capture`; escalate only unrecoverable human decisions. Do not dispatch workers,
copy a mission ledger, maintain a heartbeat, create a Routine, operate on inner
sessions, or `stop` the Host before close-out. Changing the outer Agent does not
stop the Host.
