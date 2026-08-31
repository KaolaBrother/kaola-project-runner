# Changelog

## Unreleased

- Simplified Runner transport for Issue #9: model catalogs, visible editor/activity evidence, and
  changed observations are reported to the controlling Agent instead of blocking communication.
  Cursor launch no longer materializes project files, and force stop now ends only the exact owned
  tmux session without process classification or descendant sweeps.
- Reduced validation to direct start, send, read, connection, and exact-stop proof; unusually long
  Runner procedures are treated as overengineering evidence and must be simplified. The default
  validator no longer runs the historical fake-runtime matrix.

- Added verified per-run main-model selection for all five runtimes: explicit user override first,
  otherwise a declared Runner default, with catalog resolution, literal launch parameters,
  actual-model evidence, resume re-verification, and no global-config mutation or communication gate.

- Reframed all five active Project Runner Skills as communication-only drivers. Bare invocation no
  longer implies `workflow-next`, task-mode selection, a 15-minute heartbeat, lifecycle classification,
  Cursor command materialization, or any other orchestration policy.
- Added Agent-selected native key transport (`up/down/left/right/enter/escape/tab/backtab/space`) with
  exact byte fingerprints. Kimi 0.39.1 was revalidated end-to-end through Runner-only
  trust-selection, prompt delivery, reply readback, and exact-session shutdown.
- Made optional Kaola carriers, runtime health, and Cursor authority/materialization preflight facts
  advisory so missing Workflow setup cannot block starting a usable CLI communication channel.

- Made interaction evidence-first across Grok, Claude Code, OpenCode, Kimi CLI, and Cursor CLI:
  raw frames and exact tmux/process/relay facts go to the controlling agent, while coordinates,
  fixed placeholders, editor/activity/approval labels, and worker counts no longer authorize or
  block generic send/stop. Skills now teach observe, agent decision, prompt transfer, response
  reading, retained-draft recovery, and durable Workflow verification.
- Removed evidence-derived hard gates from agent-directed transport. `send` and `stop` no longer
  require a snapshot; a caller-supplied old observation is reported through `action_time_snapshot`
  and `observation_changed:true` instead of `stale-snapshot` refusal. Later-output barriers, draft,
  approval, activity, process counts, Git, and Workflow interpretations remain evidence only.
- Removed the Cursor `cursor_x=2` input-origin blocker and the equivalent coordinate authority from
  shared placeholder interpretation. Added the real Cursor v2026.08.25 x=0 frame as evidence.
- Made mutation-refusal recovery receipts truthful: `restored:true` now requires proof of resumed
  child/process group, restored pane input, a responsive relay, and released lease;
  otherwise the receipt reports `restored:false` with explicit evidence.
- Added schema-v2 observations and a managed nested-PTY relay that record independent
  editor/approval/visible-work facts, byte/input/output/resize revisions, recovery evidence, and
  Claude whole-editor replacement receipts without turning those facts into runtime state authority.
- Added exact outer-PTY fence outcomes without replay, escaped-descendant containment, and pre-write
  terminal-control reporting with bracketed-paste-only LF/TAB handling. Prepared send/answer payloads
  retain byte-level fingerprint receipts across real newlines, TABs, and terminal soft wraps.
- Consolidated all five generated Skills on the shared relay control plane while keeping Grok's
  live-proven prompts, task modes, scheduling, claim handoff, lifecycle, and golden source bytes
  unchanged; generated transport wording is applied through an exact reversible overlay.
- Made the legacy Grok validation use its own explicitly numbered tmux server, so a user's
  `base-index` and `pane-base-index` cannot change the verdict.
- Made Claude Code decisions, approval surfaces, retained editors, and later-output barriers visible
  to the controlling agent without blocking that agent's chosen follow-up transport.
- Made execution cadence caller-controlled across every runner Skill; runtime-native recurring
  support no longer gates an outer Codex heartbeat or scheduler.
- Added the live-proven Claude Code launch profile, stable tmux pane targeting, dynamic-title TUI
  detection, and native approval classification.
- Initialized Kaola-Workflow documentation structure.
