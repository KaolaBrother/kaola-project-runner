# Codex supervision heartbeat

This skill targets Codex only. Every started or resumed project run gets one lightweight 15-minute
Codex heartbeat attached to the current thread. Its job is to supervise and report, not to become a
second project owner.

This heartbeat is different from the optional Kimi CLI scheduler:

- **Codex heartbeat:** always created for an active run; observes status and reports to the user.
- **Kimi CLI foreground scheduler:** created only when the user explicitly requests recurring project
  execution; each firing runs in the same Kimi CLI main orchestrator.

## Create or update

Use Codex's current thread heartbeat/automation mechanism, not a shell `sleep`, background process,
standalone cron project, or detached agent. Prefer updating the heartbeat already associated with
this exact repository, tmux session, and Kaola run over creating a duplicate.

Schedule it every 15 minutes. Its prompt must include stable exact identifiers and this contract:

```text
Supervise the active Kimi CLI Kaola project run.

Repository: {absolute repo root}
Tmux session: {exact session}
Kaola project or targets: {project and issue/PR set when known}

Use the kimi-cli-kaola-project-runner status contract. Inspect only the exact owned tmux session and
repository. Read Kimi CLI activity, Git branch/HEAD/cleanliness/ahead-behind, the relevant
workflow-state.md and mission-list.md, and fresh exact Issue/PR state when available. Do not inject
while Kimi CLI is busy and do not create another Kimi CLI scheduler or project claim.

Report a concise status to the user: Kimi CLI state, Git state, mission counts, forge state,
classification, next safe action, and any HUMAN_DECISION_REQUIRED. If the run is still active,
leave this heartbeat active for the next 15-minute check. If complete, verify finalization, sink,
remote state, archive, and cleanup, then delete this exact heartbeat after reporting the final
result. If uncertain, preserve the run and report the missing evidence.
```

Record the returned heartbeat ID in the Codex thread and include it in status reports.

## On each firing

1. Perform read-only observation first.
2. Report even when the state is unchanged, but keep it concise.
3. Never interrupt active Kimi CLI work merely to obtain a response.
4. If `HUMAN_DECISION_REQUIRED` is pending, surface that exact decision from the main conversation;
   do not answer it or duplicate it in a child.
5. If a terminal state is genuinely verified, report it and delete this exact heartbeat.
6. If the exact tmux session is absent before completion evidence exists, classify `uncertain` or
   `interrupted`; do not silently declare success or create a replacement without reconciling Git
   and Kaola state.

Do not use a recurring heartbeat to broaden the user's original authority. It supervises only the
run that caused it to be created.
