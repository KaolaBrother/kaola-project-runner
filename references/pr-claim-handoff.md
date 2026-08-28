# PR claim handoff

Apply this contract before every one-shot or recurring PR review, before `workflow-next`, before a
writable checkout, and before creating or reconstructing `kaola-workflow/{project}`.

## Measure first

Read fresh PR head/base, closing or linked Issues, body, comments, checks, and merge state. For every
linked Issue, read current labels and comments and extract active `workflow:in-progress` state plus
the exact `<!-- kw:claim project={project} -->` marker. Compare the claimed project with the PR head
branch and with every other Issue in the PR close set.

Do not infer ownership from the GitHub account alone: a remote author session and the local reviewer
can use the same account while remaining distinct Kaola owners.

## Classify exactly once

### `UNCLAIMED_PR`

No linked Issue has an active claim marker or in-progress label.

- The Grok main conversation may use `workflow-next` to claim and review the exact PR.
- After its mission frontier completes, use `kaola-workflow-finalize` normally.

### `ORIGIN_PR_HANDOFF`

Every linked Issue in the close set has the same claim project, and the PR head is the authoring
branch for that project, normally `workflow/{project}`. The claim is the originating run's
intentional PR-sink footprint while review is pending.

- Do not call workflow startup or claim the linked Issues.
- Do not resume, adopt, copy, or reconstruct the authoring run's active folder, mission list,
  worktree, session marker, or sink metadata.
- Do not convert its `sink: pr` lifecycle into a second `sink: merge` run.
- Review the frozen PR candidate without taking Kaola ownership. Read-only review and validation may
  use isolated temporary worktrees; do not push repairs while the author claim is active. Findings
  return to the main conversation as `HUMAN_DECISION_REQUIRED` or an explicit author-handoff request.
- If review passes, merge the PR through the authorized forge path. Then run the installed
  `watch-pr` sweep only when the originating run's exact local state is present; never synthesize
  that state merely to make cleanup run. If the state is remote-only, report
  `MERGED_AWAITING_ORIGIN_WATCH_PR` and leave its claim for the owner/successor to settle.

### `FOREIGN_CLAIM_CONFLICT`

Any linked Issue is claimed by a different project/branch, bundle members have different claims, the
PR head does not match the claimed project, multiple markers conflict, or evidence is incomplete.

- Do not invoke `workflow-next`, work offline, create workflow state, checkout a writable branch,
  dispatch repair agents, merge, close Issues, clear labels, or delete claim markers.
- Report `CLAIM_CONFLICT` with PR, Issue set, claim project(s), head branch, and missing or conflicting
  evidence. Continue to another independent PR only when the recurring task authorized it.

## Refused startup is terminal routing evidence

If startup returns `target_set_conflicts_active_work` or any equivalent occupied/claimed envelope,
stop that route. Never reinterpret the refusal as permission to reconstruct the same project under a
new session marker, attach the other run's branch, or proceed with a different sink. Re-measure and
classify the PR; only the three paths above are allowed.

## Classification examples

| Linked-Issue evidence | PR head | Class |
|---|---|---|
| no active label or marker | any authorized head | `UNCLAIMED_PR` |
| every Issue says `project=bundle-a-b` | `workflow/bundle-a-b` | `ORIGIN_PR_HANDOFF` |
| Issue says `project=bundle-a-b` | `workflow/issue-c` | `FOREIGN_CLAIM_CONFLICT` |
| bundle members name different projects | any head | `FOREIGN_CLAIM_CONFLICT` |
| label exists but marker/branch evidence is missing | any head | `FOREIGN_CLAIM_CONFLICT` |
