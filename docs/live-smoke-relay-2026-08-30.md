# Five-runtime managed-relay smoke — 2026-08-30

This record covers the real-CLI validation for Issue #6. Every runtime used its exact
`kpr-issue6-live-*` tmux session and the generated platform Skill's managed nested-PTY relay. The
prompt was exactly `workflow-next` under a read-only validation boundary: Issue #6 was already owned
by this Kaola run, so the smoke conversations were not authorized to claim, edit, finalize, or close
it.

## Runtime matrix

| Platform | Version | Guarded input evidence | Workflow boundary | Exact shutdown |
|---|---|---|---|---|
| Grok CLI | `1.0.13` | Fresh schema-v2 snapshot accepted one literal `workflow-next` submit | Loaded the installed workflow and recognized active Issue #6; reported the existing state without claim, write, fetch, or finalize | Session absent after exact stop |
| Claude Code | `2.1.246` | Equivalent full redraws advanced output digest/pane revision while preserving the mutation snapshot; guarded submit returned `result=sent` and the TUI echoed `❯ workflow-next` | Returned `Login expired · Please run /login`; command receipt only, no Workflow execution claimed | Force stop proved session, child, child group, and epoch socket absent |
| OpenCode | `1.18.23` | Fresh snapshot accepted the prompt in the attested OpenCode TUI | Loaded `workflow-next`, recognized active Issue #6, and completed read-only ownership/state checks | Session absent after exact stop |
| Kimi CLI | `0.39.1` | Relay reached and classified the native `Trust this folder?` screen as `native_approval.kind=workspace-trust` | Prompt was deliberately not sent: trusting persists a user-level project decision and enables project MCP, which this smoke did not own | Force stop proved session, child, child group, and epoch socket absent |
| Cursor CLI | `2026.08.25-3e8eec8` | Fresh snapshot accepted the prompt after official receipt-backed project materialization | Loaded `workflow-next`, recognized active Issue #6, and completed read-only forge/local inspection | Force stop proved zero relay residue; official uninstall removed 17 managed files and preserved 0 foreign files |

Claude Code is intentionally receipt-only because this machine has no usable Claude account. Kimi
is intentionally approval-boundary-only because no authority was given to persist workspace trust.
Neither result is described as successful Workflow execution.

## Transport findings

- Real Claude Code emits a byte-distinct but visually equivalent full redraw after each relay resume.
  `pane_revision` remains the complete transport report, while `snapshot_id` excludes output-only
  counters/digests and binds the equal visible frame, editor, identity, input, process, approval,
  barrier, and Git facts. The live guarded submit and deterministic SIGCONT fixture both pass.
- Runtime launcher/worker descendants remain exact snapshot facts but are not interpreted as busy by
  the shell. The controlling model reads their meaning together with visible editor/work evidence.
- Relay control requests and half-open sockets are bounded. Caught failures restore only the exact
  child group; terminal force stop reconciles transport loss against session, child, process-group,
  socket, and pane-input facts before reporting success.
- The startup deadline is measured once against wall clock; expensive observation cannot multiply
  the configured timeout.

These changes affect only observation and guarded transport. Grok prompts, project/PR modes,
scheduling, claim handoff, lifecycle, and closing semantics retain their frozen live-proven bytes.
