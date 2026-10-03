---
name: kaola-delegator
description: "Use when an outer Agent (Grok Bot, Codex, or generic) should delegate a project run through Kaola-Delegator to one CLI Host on any platform: extract the task, progress, Host platform, authorization, quota, priority, start or resume that Host via its platform Runner, and relay user changes without dispatching workers."
---

# Kaola-Delegator

This Skill is the external delegation Skill for Grok Bot (post-bridge),
Codex, and generic hosts, not Project Runner or a platform worker.

Project Runner (`kaola-project-runner`) is the inner control-plane Skill. One
CLI Host loads it and owns planning, worker dispatch, path binding,
heartbeat, acceptance, and Workflow close-out. Do not copy that engine; one
project runs only one Agent for it.

## Extract once

From the user and Git/Workflow/Issue/Runner records collect:
goal; progress; the Host platform; authorized worker platforms by class;
Elite grants/counts; Expert grants/lifetime; bound-target local choices
separate from authorization (host-platforms.md); Worker pool rules;
exclusions; the quota the user actually gave, each figure in its own unit;
priority; delivery/stop boundary; project path.
On a live Host, apply only the user's latest change; consolidate nonurgent corrections at latest values; urgent owner stops go now. Relay explicit owner model/seat choices unchanged; the Host allocates. Invent no assignments/constraints. On a new Host, missing,
conflicting, or expired key values must be confirmed before `start`. A quota
unit the user never gave is not a missing key value — carry it as unspecified
and start; a quota whose unit is unclear is, so ask. Do not open a blank Host.
Do not invent platforms, fuse quota units, raise quota, treat an unspecified
quota as unlimited, reuse a stale quota, or expand authorization.

## One Host

Select any supported Host platform
([host-platforms.md](references/host-platforms.md)) and use its own Runner
`<platform>-kaola-project-runner`, entry line, native resume id. If that Runner
is missing, report not executable; claim no Host.

One live Host per repo, whatever its platform. Recover at canonical root: `<platform>-<PROJECT_CODE>-orchestrator-<purpose>` and Runner receipts; A Git worktree is not an ACP id. Attach exact verified identity even if its recorded name is not the new form. `host-exists` means attach its `existing_host`; never rename and retry. Missing standard name permits no second Host. Failed identity is exact-stopped, proven gone (`residual_pids: []`) before replacement. Resume with attested native id; authorize before start. Never restart in-flight work; interrupt/cancel only for urgent scoped owner stops. [Bricked or quota-exhausted Host](references/host-brick.md); never log in. Grok Bot account bridge attests via locator; Codex/generic don't. Start/resume/replace/attach: [handoff.md](references/handoff.md).

Pass no per-worker `--repo`, scheduling, or heartbeat instructions.
Exact Host `stop` and live attach use `holder_instance_id` from its
receipt (`--expected-holder-instance-id`); a different holder is not that Host.

## After the handoff

Relay user changes to the same Host: idle `send`; busy `steer` or wait for idle
(no queue). `--no-wait` admission and Host `end_turn` are not delivery. After
the first Host beat, verify file/work-product evidence and the first dispatch
receipt against plan and authorization; do not trust the Host's self-description.
Correct mismatches on this Host; do not accept completion. At cadence, read the [snapshot (`sweep=` line)](references/snapshot.md) and observe/capture outcomes. Pass valid evidence forward; recheck only changed facts or gaps. Relay pacing if warranted; escalate unresolved human decisions. Do not dispatch workers, copy a mission ledger, write the Host heartbeat, create a Routine, touch inner sessions, or stop before close-out. Changing the outer Agent does not stop it.

KPR update: [host-platforms.md](references/host-platforms.md#kpr-updates); a notice proves no updated install or loaded guidance, authorizes no install/restart.
