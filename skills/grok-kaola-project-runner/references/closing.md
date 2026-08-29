# Closing a task mode

Closing is a lifecycle operation, not merely killing tmux. Preserve the Grok main conversation until
Kaola and Git evidence settle the selected work.

## One-shot Workflow or PR mode

1. Read Grok, Git, `workflow-state.md`, `mission-list.md`, and exact forge state.
2. If work remains, classify `in-progress` or `waiting-human`; do not close it as complete.
3. When all missions are done, have the same Grok main conversation use
   `kaola-workflow-finalize`.
4. For PR work, prove the PR merged and every exact linked/closing Issue is terminal. Prefer the
   originating run's `watch-pr`; when its state is absent or cleanup fails, remove only matching
   claim marker(s) and `workflow:in-progress` label(s) after merge/completion proof. Never clean
   foreign, mismatched, open unfinished, or ambiguous residue; ambiguity requires
   `HUMAN_DECISION_REQUIRED`.
5. Verify validation, sink, remote main/PR/Issue state, zero matching claim residue, archive, and
   owned cleanup.
6. When the exact owned Grok session is idle, stop it with `scripts/grok-tmux.sh stop` if the user or
   operating agreement requested session shutdown.
7. Report the final result, then delete the exact Codex supervision heartbeat.

## Recurring Workflow or PR mode

When the user asks to end recurring work or its authorized terminal condition is reached:

1. Inspect the exact main conversation and `/tasks`. If a firing is active, wait; do not interrupt it
   or start a duplicate closing turn.
2. Preserve any unresolved `HUMAN_DECISION_REQUIRED`; recurring shutdown does not authorize an
   answer or abandonment.
3. In the idle main conversation, cancel exactly the scheduler owned by this mode. Verify the exact
   scheduler ID is absent, the matching scheduler count is zero, and no detached firing remains.
4. Reconcile any active Kaola run. Finalize it when every mission is complete; otherwise report the
   real incomplete state rather than calling the recurring mode closed.
5. For every merged PR, settle exact completed linked-Issue claim residue through origin `watch-pr`
   or the proven direct fallback; preserve foreign/unfinished residue and stop on ambiguity.
6. Verify Git, forge, sink, terminal Issue state, zero matching claim markers and in-progress labels,
   archive, clean alignment, zero owned scheduler/detached intake, and cleanup.
7. Gracefully stop only the exact owned idle tmux session when requested. Never stop the tmux server
   or another session.
8. Report the final state and delete the exact Codex supervision heartbeat.

An absent tmux session is completion evidence only when Kaola, Git, and forge terminal evidence also
exists. Otherwise classify the run as `interrupted` or `uncertain` and reconcile before recreating or
closing anything.
