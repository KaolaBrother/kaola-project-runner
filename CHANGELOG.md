# Changelog

## Unreleased

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
