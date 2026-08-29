# Lightweight status monitoring

Use CLI evidence to supervise progress without taking ownership away from Grok. Monitoring is
read-only except for an explicitly requested remote refresh.

Codex performs this check from the current thread heartbeat every 15 minutes while the run is
active. See [codex-supervision.md](codex-supervision.md).

## Observe the three state surfaces

### Grok and tmux

```bash
scripts/grok-tmux.sh status --repo "$REPO" --session "$SESSION"
scripts/grok-tmux.sh capture --repo "$REPO" --session "$SESSION" --lines 120
```

Determine whether the main conversation is busy, idle, waiting on a user decision, absent, or
uncertain. Do not send a status question merely because work is still running.

### Git and Kaola Workflow

The helper status includes the basic Git snapshot. When more context is needed, use:

```bash
git -C "$REPO" status --short --branch
git -C "$REPO" log -1 --oneline --decorate
git -C "$REPO" diff --stat
git -C "$REPO" diff --cached --stat
```

Read the relevant active `workflow-state.md` and `mission-list.md`. Count `done`, `in-flight`, and
`todo` items; inspect output locators before deciding an in-flight item was lost. Git cleanliness by
itself never proves that the workflow is complete.

### Forge

When GitHub is in scope and `gh` is authenticated, refresh only the exact Issue or PR owned by this
run. Inspect its current state, checks, merge status, comments, and remote branch/main truth. A local
commit or merged PR alone does not prove Issue closure, Kaola archive, or sink completion.

For PR work, also report `claim_class` from
[pr-claim-handoff.md](pr-claim-handoff.md). A same-branch origin claim is not evidence that the
reviewer owns the run. Also report `workflow_next_result`: an origin-handoff refusal may be
`claim:none, ignored-for-review`, but a reconstructed author folder is still not ownership or resume
success.

## Classify and report

Use one of these concise states:

- `not-started`: no owned Grok/Kaola run exists.
- `in-progress`: Grok or a mission item is actively working.
- `waiting-human`: the main conversation has an unresolved `HUMAN_DECISION_REQUIRED`.
- `ready-to-finalize`: all missions are done but finalization evidence is not complete.
- `finalizing`: final validation, sink, push, closure, or archive is active.
- `complete`: the selected work is validated, sunk, reflected remotely, and archived.
- `uncertain`: evidence conflicts or a required surface cannot be checked.

Report only:

```text
Project: <repo and Kaola project>
Grok: <session, main conversation state>
Git: <branch, short HEAD, clean|dirty, ahead|behind when known>
Mission: <done / in-flight / todo>
Forge: <Issue/PR state or unavailable>
Status: <classification>
Next: <next safe action>
Decision: <none or one concrete user decision>
```

Keep monitoring proportional. If work is active, estimate a sensible later check rather than
polling or interrupting the main conversation.
