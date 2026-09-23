<!-- KPR-USER-COMPACT-RECOVERY-START -->
Recovery marker: `KPR-USER-COMPACT-RECOVERY-V1` (Project Runner, user-level Codex hook).

Context was just compacted. This applies only if this session was already using
the `kaola-delegator` or `kaola-project-runner` Skill before compaction — the
evidence is in this context (a Skill invocation, a Host handoff, Runner
receipts). Otherwise ignore it: do not start delegation or project work, and
never infer a role or a project from the working directory.

If it applies:
1. Completely re-read that installed Skill from its installed directory
   (`~/.codex/skills/kaola-delegator` or `~/.codex/skills/kaola-project-runner`,
   or the `$CODEX_HOME` you loaded it from), not from memory. This hook is a
   pointer, not the Skill.
2. Continue from existing records only — current authorization, the live ACP
   session and Runner `status` receipts, and Git, worktree, Workflow, and Issue
   records. Do not re-intake, re-claim, start a second Host, resend prompts, or
   re-dispatch in-flight work.

This hook performs no dispatch, edits no state, and keeps no binding table,
session registry, or heartbeat.
<!-- KPR-USER-COMPACT-RECOVERY-END -->
