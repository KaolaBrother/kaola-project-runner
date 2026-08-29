# Execution cadence and scheduling

The human or invoking agent chooses the execution carrier and its cadence. Available choices include
one-shot execution, a Codex thread heartbeat, and a runtime-native same-main-conversation scheduler
when the caller selects it and its current interface is live-verified. Runtime-native recurring
support informs carrier selection; it never gates an authorized outer Codex carrier.

Scheduling changes when work runs; it does not replace the project-run contract. Use one carrier
identity for the selected scope and never overlap two firings for the same run.

## Carrier selection

- **One-shot:** run one bounded batch and finish after terminal evidence.
- **Codex thread heartbeat:** use [codex-supervision.md](codex-supervision.md) either for observation
  only or as the execution carrier. Record which role it owns, its ID, interval, active window, and
  stopping condition.
- **Runtime-native scheduler:** when selected, inspect the current Kimi CLI interface in the
  owned idle main conversation, create the scheduler using its authoritative live schema, and verify
  its identity, cadence, main-conversation routing, and stopping behavior from runtime evidence.

## Every firing

1. Re-read the exact repository, Git, forge, Kaola run, and selected-carrier state.
2. Resume an active batch only when the Kimi CLI main conversation is its verified owner or
   successor. Never overlap it with a new batch.
3. For project intake, invoke `workflow-next` without an individual Issue target and remain within
   the authorized recurring goal.
4. For PR intake, query fresh open-PR truth, classify linked-Issue claims, and invoke
   `workflow-next` for every selected PR. Preserve `claim:none` for `ORIGIN_PR_HANDOFF`; treat a
   foreign or ambiguous `kw:claim project=` or `workflow:in-progress` marker as a conflict.
5. Surface `HUMAN_DECISION_REQUIRED` in the owning main conversation and end that firing without
   starting duplicate work.
6. Use `kaola-workflow-finalize` only after the mission frontier is complete. For an origin PR
   handoff, finish the clean review, merge, and use the originating `watch-pr` cleanup instead of a
   second reconstructed finalization.
7. Before another firing, record terminal, waiting-human, or honestly uncertain evidence for the
   current one.

For PR repairs, verify the current head immediately before mutation; a head advance requires
re-review or `HUMAN_DECISION_REQUIRED`. Empty intake performs no repository or Issue mutation.

## Carrier verification and closure

Record the selected carrier type and exact identity, interval, active window, stopping condition,
repository, tmux session, and authority boundary. A real firing must enter the intended
Kimi CLI main conversation. Verify that stopping, pausing, or updating this carrier affects
no unrelated carrier or tmux session.

At the selected terminal condition, finish or classify the active firing, reconcile finalization,
Git, forge, claim cleanup, archive, and sink evidence, then apply the selected disposition to that
exact carrier. Report the final carrier state together with the run evidence.
