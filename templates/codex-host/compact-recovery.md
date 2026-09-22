<!-- KPR-COMPACT-RECOVERY-START -->
# Project Runner compact recovery (Codex host)

Recovery marker: `KPR-COMPACT-RECOVERY-V1`.

The conversation context was just compacted. Recover before the next
project-level decision or dispatch:

1. Confirm your role. You are a Codex host Agent using the installed
   `kaola-project-runner` Skill — or `kaola-delegator`, if that is the Skill in
   use. This hook is only a pointer; it is not the Skill and never replaces it.
2. Completely re-read the installed Skill for your role, from its installed
   directory, not from memory (Project Runner default:
   `~/.codex/skills/kaola-project-runner`).
3. Recover the live scene from the project's own records, newest first: current
   authorization (allowed CLIs, counts, models), the effective-now heartbeat,
   and run records — Runner session records, plus Workflow `workflow-state.md`
   and `kaola-workflow/.ledger/issue-<N>.jsonl` when present.
4. Continue the same frontier. Do not re-intake, re-claim, restart Hosts or
   workers, resend prompts, or re-dispatch work whose locator is already in
   flight. Reconcile in-flight locators before any new dispatch.

Boundaries: this hook performs no dispatch, edits no project state, and keeps
no second copy of the Skill, mission ledger, or heartbeat. Missing or conflicting
authorization facts are asked, never invented.
<!-- KPR-COMPACT-RECOVERY-END -->
