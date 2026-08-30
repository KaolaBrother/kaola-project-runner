# Changelog

## Unreleased

- Replaced authoritative idle-gated mutation with schema-v2 evidence snapshots and a managed
  nested-PTY relay. Every send, ordinary/force stop, and supported decision answer now rechecks an
  exact fresh snapshot after child-process quiescence and a tokenized tmux parser fence.
- Added independent editor/approval/visible-work facts, relay byte/input/output/resize revisions,
  stale-snapshot refusals, legacy-direct reporting-only migration, and a Claude-only public answer
  operation with replacement receipts plus pending/output-seen/satisfied later-output barriers.
- Added prepared-surface revalidation, exact outer-PTY fence refusal without replay, cursor-bound
  Claude/Cursor/OpenCode placeholder recognition, escaped-descendant containment, and pre-write terminal
  control rejection with bracketed-paste-only LF/TAB handling. Prepared send/answer editors now bind
  the exact payload across real newlines, TABs, and terminal soft wraps before Enter.
- Consolidated all five generated Skills on the shared relay control plane while keeping Grok's
  live-proven prompts, task modes, scheduling, claim handoff, lifecycle, and golden source bytes
  unchanged; generated transport wording is applied through an exact reversible overlay.
- Made the legacy Grok validation use its own explicitly numbered tmux server, so a user's
  `base-index` and `pane-base-index` cannot change the verdict.
- Made Claude Code decision conflicts fail closed: a visible pending Workflow decision plus an
  editor, whether empty or populated, can no longer be reported as idle or accept `send`; later
  runtime output must replace pending evidence in the current activity tail before a fresh empty
  prompt clears stale decision history.
- Made execution cadence caller-controlled across every runner Skill; runtime-native recurring
  support no longer gates an outer Codex heartbeat or scheduler.
- Added the live-proven Claude Code launch profile, stable tmux pane targeting, dynamic-title TUI
  detection, and native approval classification.
- Initialized Kaola-Workflow documentation structure.
