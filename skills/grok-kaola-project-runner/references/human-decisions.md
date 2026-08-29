# Human decisions in the main conversation

Kaola Workflow leaves irreversible and value-laden decisions in conversation. Because a detached
loop cannot reliably surface those decisions to the user's project intake, the Grok main
conversation must retain ownership.

## Return to the user before acting

Examples include:

- destructive Git operations, force pushes, or history rewrites;
- real content-conflict resolution;
- deployment, credentials, production data, schema, or public API changes not already authorized;
- deleting working capability or user data;
- creating, closing, splitting, merging, or reorganizing issues when the right outcome is unclear;
- closing an issue that still contains open work;
- accepting missing physical, service, or environment validation;
- changing the user's stated target, priority, or definition of done.

## Required Grok response

```text
HUMAN_DECISION_REQUIRED
Decision: <one concrete question>
Evidence: <facts and locators>
Recommendation: <recommended option and why>
Safe options:
1. <option and consequence>
2. <option and consequence>
Paused state: <project, mission item, branch/worktree, and what remains untouched>
```

Grok then waits in the same main conversation. The controlling Agent reports the question to the
user and sends the answer back to that conversation only after the session is idle. No durable
approval file, scheduler, detached worker, or inferred preference substitutes for the answer.
