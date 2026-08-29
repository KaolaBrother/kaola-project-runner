# Closing a task mode

Closing is a lifecycle operation, not merely killing tmux. Preserve the Cursor CLI main conversation until
Kaola and Git evidence settle the selected work.

## One-shot Workflow or PR mode

1. Read Cursor CLI, Git, `workflow-state.md`, `mission-list.md`, and exact forge state.
2. If work remains, classify `in-progress` or `waiting-human`; do not close it as complete.
3. When all missions are done, have the same Cursor CLI main conversation use
   `kaola-workflow-finalize`.
4. For PR work, prove the PR merged and every exact linked/closing Issue is terminal. Prefer the
   originating run's `watch-pr`; when its state is absent or cleanup fails, remove only matching
   claim marker(s) and `workflow:in-progress` label(s) after merge/completion proof. Never clean
   foreign, mismatched, open unfinished, or ambiguous residue; ambiguity requires
   `HUMAN_DECISION_REQUIRED`.
5. Verify validation, sink, remote main/PR/Issue state, zero matching claim residue, archive, and
   owned cleanup.
6. When the exact owned Cursor CLI session is idle, stop it with `scripts/runtime-tmux.sh stop` if the user or
   operating agreement requested session shutdown.
7. Report the final result. If a Codex heartbeat exists, apply the caller-selected terminal
   disposition to that exact heartbeat.

## Recurring Workflow or PR mode

When the caller asks to end recurring work or its selected terminal condition is reached:

1. Inspect the exact main conversation and the selected execution carrier. If a firing is active,
   wait; do not interrupt it or start a duplicate closing turn.
2. Preserve any unresolved `HUMAN_DECISION_REQUIRED`; recurring shutdown does not authorize an
   answer or abandonment.
3. Stop, pause, or update exactly the carrier owned by this mode according to its operating
   contract. Verify its exact identity and intended terminal disposition, and prove no firing
   remains active.
4. Reconcile any active Kaola run. Finalize it when every mission is complete; otherwise report the
   real incomplete state rather than calling the recurring mode closed.
5. For every merged PR, settle exact completed linked-Issue claim residue through origin `watch-pr`
   or the proven direct fallback; preserve foreign/unfinished residue and stop on ambiguity.
6. Verify Git, forge, sink, terminal Issue state, zero matching claim markers and in-progress labels,
   archive, clean alignment, selected carrier disposition, zero overlapping intake, and cleanup.
7. Gracefully stop only the exact owned idle tmux session when requested. Never stop the tmux server
   or another session.
8. Report the final state and the exact selected carrier disposition.

An absent tmux session is completion evidence only when Kaola, Git, and forge terminal evidence also
exists. Otherwise classify the run as `interrupted` or `uncertain` and reconcile before recreating or
closing anything.
