# PR claim handoff

Apply this contract before every one-shot or recurring PR review, then invoke `workflow-next` with
the measured result before a writable checkout or any workflow-state creation.

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

- The Kimi CLI main conversation may use `workflow-next` to claim and review the exact PR.
- After its mission frontier completes, use `kaola-workflow-finalize` normally.

### `ORIGIN_PR_HANDOFF`

Every linked Issue in the close set has the same claim project, and the PR head is the authoring
branch for that project, normally `workflow/{project}`. The claim is the originating run's
intentional PR-sink footprint while review is pending.

- Invoke `workflow-next` to review the exact PR and explicitly explain that the existing claim is
  the authoring PR-sink run's expected handoff footprint.
- If startup returns `target_set_conflicts_active_work` or an equivalent occupied envelope, ignore
  that conflict **only as a blocker to continuing the PR review**. Preserve its `claim: none`
  result; do not retry or claim the linked Issues.
- Do not resume, adopt, copy, or reconstruct the authoring run's active folder, mission list,
  worktree, session marker, or sink metadata.
- Do not convert its `sink: pr` lifecycle into a second `sink: merge` run.
- Continue the workflow-driven PR review without taking Issue ownership. Use an isolated PR
  worktree when useful. In-scope review repairs may update the PR branch only after refreshing the
  head and proving it has not advanced since the candidate was reviewed; they never mutate the
  author's workflow metadata or claim. A conflicting concurrent head advance requires re-review or
  `HUMAN_DECISION_REQUIRED`, not an overwrite.
- If review passes, merge the PR through the authorized forge path. Then run the installed
  `watch-pr` sweep when the originating run's exact local state is present; never synthesize that
  state merely to make cleanup run. If the origin folder/state is absent or `watch-pr` cannot
  perform cleanup, do not leave `MERGED_AWAITING_ORIGIN_WATCH_PR` indefinitely. After proving the
  PR is merged and every Issue in the exact linked/closing set is completed and closed, or closing
  it under the user's authorized completion decision, directly remove only that originating
  project's matching `<!-- kw:claim project=... -->` marker(s) and
  `workflow:in-progress` label(s). Never remove a foreign/mismatched claim or residue from an open
  unfinished Issue. Ambiguous ownership or completion mapping requires
  `HUMAN_DECISION_REQUIRED` before mutation.

### `FOREIGN_CLAIM_CONFLICT`

Any linked Issue is claimed by a different project/branch, bundle members have different claims, the
PR head does not match the claimed project, multiple markers conflict, or evidence is incomplete.

- Invoke `workflow-next` with the conflict evidence so the required workflow command records and
  explains the review routing. Do not tell it to ignore a foreign or ambiguous ownership conflict.
- Report `CLAIM_CONFLICT` with PR, Issue set, claim project(s), head branch, and missing or
  conflicting evidence. Do not create workflow state, checkout a writable branch, dispatch repair
  agents, merge, close Issues, clear labels, or delete claim markers. Continue to another
  independent PR only when the recurring task authorized it.

## Refused startup has two separate meanings

If startup returns `target_set_conflicts_active_work` or any equivalent occupied/claimed envelope,
the refusal is terminal evidence that this reviewer acquired no ownership. When fresh evidence has
already established `ORIGIN_PR_HANDOFF`, it is not terminal for PR review: explain the author's
PR-sink handoff, ignore the conflict as a review blocker, and continue without claiming. For
`FOREIGN_CLAIM_CONFLICT`, stop after the workflow invocation and report the conflict. In neither
case may the reviewer reconstruct the same project under a new session marker, attach or adopt the
other run's workflow state, clear a claim before merge/completion proof, or change its sink. The
post-merge exact-residue fallback above is cleanup of a completed handoff, not acquisition of the
originating run.

## PR terminal evidence

Neither merge nor Issue closure is terminal by itself. Every one-shot or recurring PR path must
prove the PR is merged, every linked/closing Issue is terminal, the completed Issue set has zero
matching `kw:claim` markers and zero `workflow:in-progress` labels, runner scheduler and detached
intake counts are zero, the repository is clean and aligned, and tmux/session shutdown follows the
operating agreement. Preserve foreign claims and unfinished Issues outside that exact close set.

## Classification examples

| Linked-Issue evidence | PR head | Class |
|---|---|---|
| no active label or marker | any authorized head | `UNCLAIMED_PR` |
| every Issue says `project=bundle-a-b` | `workflow/bundle-a-b` | `ORIGIN_PR_HANDOFF` |
| Issue says `project=bundle-a-b` | `workflow/issue-c` | `FOREIGN_CLAIM_CONFLICT` |
| bundle members name different projects | any head | `FOREIGN_CLAIM_CONFLICT` |
| label exists but marker/branch evidence is missing | any head | `FOREIGN_CLAIM_CONFLICT` |
