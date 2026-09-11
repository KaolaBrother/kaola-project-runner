# Architecture: Evidence-Only Five-Runtime Interaction

## Decision

Kaola Project Runner Skills discover and transfer; they do not decide or block. The same authority
boundary applies to Grok CLI, Claude Code, OpenCode, Kimi CLI, and Cursor CLI.

Cursor live acceptance has one additional experiment protocol: the validating Agent explicitly selects
a non-FAST Cursor Grok 4.6 variant through `/model`, captures the selection, then runs the communication
prompt. This constrains validation evidence, not the Runner's general communication API.

The Skill:

1. starts or reuses the exact named tmux session;
2. observes and captures the complete visible frame;
3. reports terminal, process, relay, input/output, repository, Workflow, and forge facts;
4. transfers the prompt or command selected by the controlling agent;
5. observes and reads the actual response; and
6. reports durable state and the objective transport outcome.

It has no default command. A bare invocation does not start `workflow-next`, choose a task mode,
schedule a heartbeat, materialize project commands, classify lifecycle state, or finalize work.

The controlling agent decides whether the runtime is busy, idle, waiting, complete, holding a draft,
asking for approval, presenting trust/login, requiring a human decision, or needing recovery.

## No evidence-derived hard gates

Generic `send` and `stop` do not branch on:

- snapshot or pane-revision changes;
- activity, editor, approval, decision, or worker-count labels;
- cursor coordinates, fixed rows, placeholders, prompt glyphs, spinners, or prose;
- child-process presence as a semantic busy signal;
- Git, Workflow, Issue, PR, claim, mission, or completion interpretation; or
- later-output barriers.

An optional snapshot links a receipt to the evidence the agent used. The action-time receipt reports
the current snapshot and whether the observation changed. Change is evidence, not `stale-snapshot`
refusal.

Compatibility observations may remain while callers migrate, but they are clearly advisory and are
returned as `evidence_flags`, not authorization failures.

## Mechanical transport outcomes

The transport still reports when it objectively could not do the requested operation: the exact
session is absent, no single target pane or managed relay is mechanically available, the relay
disconnects, literal bytes cannot be represented, payload preparation/attestation fails, or submission
cannot be confirmed. These are non-execution facts, not semantic status verdicts.

A transport receipt reports:

- requested/based-on observation identifier, when supplied;
- action-time observation identifier and `observation_changed`;
- whether bytes were prepared and submitted;
- literal payload fingerprint without plaintext;
- before/after relay input/output facts; and
- recovery evidence.

`restored:true` requires fresh positive proof that the child/process group resumed, pane input is
enabled, the relay responds, and lease/mutation lock are released. Otherwise it is false.

## Platform interaction contract

Every generated Skill teaches the same loop:

```text
observe + capture
  -> controlling agent reads all evidence and chooses
  -> send the chosen prompt
  -> observe + capture the actual response
  -> agent handles output, drafts, approvals, decisions, login/trust, and errors
  -> verify workflow-state.md, mission-list.md, branch/worktree, forge and lifecycle facts
```

Adapters contribute only measured platform facts: executable, launch/continue/resume syntax, visible
product evidence, quit text, and mechanically proven input capabilities. They do not define a platform
state machine.

Native selection screens use the same rule. The Agent reads the frame and chooses a named key; the
Runner sends only the exact key bytes, without inferring option semantics or adding Enter.

A whole-editor replacement operation is an optional tested transport capability. The Skill reports
whether it is available; the agent decides whether to use it, open a clean conversation, wait, send
anyway, or ask the user.

## Grok boundary

Grok's live-proven project prompts and Workflow/task-mode/scheduling/PR-handoff/lifecycle/closing bytes
remain unchanged under `templates/grok-golden/` as historical reference evidence. The active Grok
Skill, like the other four, is communication-only and does not impose those optional orchestration
choices. Issue #7 removes shared Issue-#6-era evidence/snapshot hard gates and re-validates Grok
through a real exact tmux run.

## Acceptance evidence

Offline contracts must prove, for all five adapters:

- `send` and `stop` work without a snapshot;
- a caller-supplied stale observation produces a changed-evidence receipt and still transfers;
- contradictory activity/editor/approval/decision/worker/coordinate evidence does not block;
- the literal payload receipt matches submitted bytes;
- output is observable after transfer;
- recovery truth cannot be asserted without all postconditions; and
- generated Skills contain no evidence-derived authorization wording.

Real exact-tmux smokes record CLI version, session, pre-action evidence, prompt receipt, output
readback, `workflow-next` receipt/durable evidence, and exact-session cleanup. Claude Code is limited
to command receipt and the observed account/login boundary on this machine. Kimi trust choices remain
with the controlling agent and are not silently approved.
