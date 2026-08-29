# Codex supervision heartbeat

The human or invoking agent chooses whether to create a Codex thread heartbeat, its cadence, and
its role. Runtime-native recurring support does not control that choice.

A heartbeat can serve either role:

- **observation only:** inspect the active run and report without triggering new work;
- **execution carrier:** run the next authorized firing using
  [scheduling.md](scheduling.md), after proving that no prior firing overlaps it.

Record the selected role, exact heartbeat ID, repository, tmux session, interval, active window,
stopping condition, and authority boundary. Update an existing heartbeat for that exact scope when
appropriate instead of creating a duplicate.

## Observation-only prompt contract

```text
Supervise the active Grok Kaola project run by observation only.

Repository: {absolute repo root}
Tmux session: {exact session}
Kaola project or targets: {project and issue/PR set when known}
Stopping condition: {caller-selected terminal condition}

Use the grok-kaola-project-runner status contract. Inspect only the exact owned tmux session and
repository. Read Grok activity, Git branch/HEAD/cleanliness/ahead-behind, the relevant
workflow-state.md and mission-list.md, and fresh exact Issue/PR state when available. Do not inject
while Grok is busy and do not take project ownership away from the main conversation.

Report a concise status to the user: Grok state, Git state, mission counts, forge state,
classification, next safe action, and any HUMAN_DECISION_REQUIRED. If terminal state is verified,
report finalization, sink, remote state, archive, and cleanup. If uncertain, preserve the run and
report the missing evidence.
```

## Execution-carrier prompt contract

Use the common firing contract in [scheduling.md](scheduling.md). The heartbeat prompt also records
the exact authorized goal, cadence, active window, and stopping condition. Each firing performs a
read-only overlap check first, resumes owned active work before selecting anything new, and ends at
a terminal, waiting-human, or honestly uncertain boundary before another firing can begin.

## Every heartbeat firing

1. Perform read-only observation first.
2. Report unchanged state honestly and keep the report concise.
3. Never interrupt active Grok work merely to obtain a response.
4. Surface an unresolved `HUMAN_DECISION_REQUIRED`; do not answer it or start duplicate work.
5. Apply the caller-selected stopping condition. Update, pause, or delete this exact heartbeat only
   when its selected role and lifecycle require it.
6. If the exact tmux session is absent before completion evidence exists, classify `uncertain` or
   `interrupted` and reconcile Git, Kaola, and forge state before any replacement run.

A heartbeat carries only the authority recorded for its selected run; it does not broaden the
repository, Issue/PR set, mutations, or value decisions.
