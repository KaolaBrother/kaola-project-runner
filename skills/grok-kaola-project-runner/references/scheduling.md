# Execution cadence and scheduling

The human or invoking agent chooses the execution carrier and its cadence. Available choices include
one-shot execution, a Codex thread heartbeat, and Grok's live-verified foreground scheduler. Runtime-
native recurring support never gates whether an authorized outer Codex carrier may trigger work.

Scheduling changes when work runs; it does not replace the project-run contract. Every firing reads
fresh truth, resumes owned active work before selecting new work, invokes `workflow-next` inside the
authorized boundary, and reaches a terminal or waiting-human classification before the next firing.
Use one carrier identity for the selected scope and never overlap two firings for the same run.

## Carrier selection

- **One-shot:** run one bounded batch and finish after terminal evidence.
- **Codex thread heartbeat:** use [codex-supervision.md](codex-supervision.md) either for observation
  only or as the execution carrier. Record which role it owns, its ID, interval, active window, and
  stopping condition.
- **Grok foreground scheduler:** use the live-verified same-main-conversation flow below when the
  caller selects it. Record its scheduler ID, interval, active window, and stopping condition.

## Grok foreground scheduler flow

In an idle owned main conversation, inspect `/tasks` first. Ask Grok with one ordinary natural-
language request to use its currently available scheduler creation capability with
`foreground: true`, so each firing becomes a new turn in the same main conversation. Do not send the
`/loop` shorthand, do not create a detached `General loop`, and do not assign project intake to a
detached subagent.

Because Grok scheduler interfaces may change, inspect the current Grok version and its exposed tool
schema in the live main conversation. Do not hardcode a remembered scheduler call signature.

## Scheduled prompt contract

Each firing must:

- re-read live repository, forge, and Kaola run state;
- resume existing work only when the main conversation is its verified owner or successor;
- classify linked-Issue claims, then invoke `workflow-next` for every authorized PR review;
- for a verified origin PR handoff, explain and ignore the expected claim refusal only as a review
  blocker while preserving `claim: none` and the author's ownership;
- after an authorized merge, settle matching claim residue with exact origin `watch-pr`, or with
  the proven direct-cleanup fallback when origin state is unavailable; never defer completed
  residue into later firings;
- surface `HUMAN_DECISION_REQUIRED` in the same main conversation and stop that firing;
- use `kaola-workflow-finalize` only after the mission frontier is complete;
- perform no work when the scheduled condition is false;
- never inject an individual Issue target or override Workflow Next's coherent batch selection.

When the condition is a PR intake, the scheduled prompt should carry the versioned marker
`MAIN_THREAD_PR_INTAKE_V3_WORKFLOW_REVIEW_HANDOFF`, query fresh forge truth on every firing, process
an authorized PR set in a deterministic order, and say `NO_OPEN_PRS` without repository or Issue
mutations when none exist. Every selected PR invokes `workflow-next`. An origin PR handoff tells the
workflow to ignore its claim refusal for review only, then uses merge and `watch-pr`; a foreign or
ambiguous claim is explained by the workflow invocation and skipped without mutation.

## Verification

After creation, verify from live evidence:

- the scheduler identifier and intended interval;
- `foreground: true` from the creation call or authoritative scheduler detail, not prompt echo;
- exactly the intended scheduler count for this project;
- zero detached General-loop schedulers and zero detached project-intake subagents;
- a real firing appears as a new turn of the same Grok session;
- disabling or stopping it affects no other scheduler or tmux session.

If the first firing begins immediately, leave it running and report `created-active`. If a previous
detached loop is currently firing, do not kill it or create a duplicate; report the migration as
pending until the child is safely inactive.

## Workflow project loop template

Adapt the placeholders, then ask the Grok main conversation to use this as the scheduler prompt:

```text
PROJECT_MAIN_THREAD_LOOP: This firing is a new turn in the same Grok main conversation. Never hand
project intake to a detached General loop or detached subagent.

Repository: {absolute repo root}
Goal: {authorized recurring project goal}
Selection boundary: {authorized project goal; no individual Issue target}
Definition of done: {validation and lifecycle evidence}
Authority boundary: {authorized mutations and user decisions}

Read fresh repository, forge, and Kaola Workflow state. Resume an active batch before taking
anything new. Invoke workflow-next without an individual Issue target and let it select the most
appropriate coherent batch inside this goal. Keep mission-list.md as the recovery record and this
main conversation as the owner. If a material user decision is required, print
HUMAN_DECISION_REQUIRED with the exact decision, evidence, recommendation, and options here, pause
the affected run, and prevent later firings from duplicating it. When every mission in the batch is
done, use kaola-workflow-finalize and verify validation, sink, remote state, Issue state, archive,
and cleanup. A later authorized firing may let workflow-next select the next efficient batch. Do
not invent work or move beyond the authorized goal.
```

## PR review loop template

This is the reusable form of the tested PR Automation contract:

```text
MAIN_THREAD_PR_INTAKE_V3_WORKFLOW_REVIEW_HANDOFF: Query fresh GitHub truth for open pull requests in
{owner/repo} using gh pr list --repo {owner/repo} --state open --limit 100 --json
number,url,title,isDraft,headRefName,baseRefName,updatedAt. This firing is a new turn in the same Grok
main conversation; never hand intake to a detached General loop or detached subagent.

If the result is empty, make no repository, Issue, roadmap, branch, or worktree changes and end this
turn with NO_OPEN_PRS. Process non-draft open PRs one at a time in ascending PR number. Before any
workflow startup, fetch the PR head/base and linked Issues, then inspect every linked Issue's
`workflow:in-progress` label and `kw:claim project=...` marker.

Classify the PR using the pr-claim-handoff contract, then always invoke workflow-next with this
instruction: "Use workflow-next to review PR #{number}. The linked-Issue claim evidence is
{claim_class and exact evidence}." If no linked Issue has an active claim, let workflow-next claim
the review run normally and, after every mission item is done, use kaola-workflow-finalize.

If every linked Issue is claimed by one project and the PR head is that project's authoring branch,
classify ORIGIN_PR_HANDOFF and add this explanation to the workflow instruction: "The existing claim
belongs to the implementation run that finalized to this PR sink. If startup reports
target_set_conflicts_active_work or an equivalent occupied result, ignore that conflict only as a
blocker to reviewing this PR. Preserve claim:none; do not retry the claim, adopt or reconstruct the
author's workflow folder, change its sink, or clear its Issue markers. Continue the workflow-driven
PR review as the review handoff, not as the Issue owner." An isolated PR worktree may be used.
In-scope review repairs may update the PR branch only after fresh head verification; a concurrent
head advance requires re-review or HUMAN_DECISION_REQUIRED. If clean, merge the PR and run the
existing author's watch-pr cleanup only when its exact local state is available. Do not run
kaola-workflow-finalize a second time against reconstructed author state. If the origin folder or
state is absent, or watch-pr cannot clean, prove the PR is merged and every exact linked Issue is
completed/closed, then directly remove only the matching originating claim marker(s) and
workflow:in-progress label(s). Do not touch foreign/mismatched claims or open unfinished Issues;
ownership or completion ambiguity requires HUMAN_DECISION_REQUIRED.

If the claim belongs to another project/branch, claims differ across the bundle, or ownership is
uncertain, classify FOREIGN_CLAIM_CONFLICT. Still invoke workflow-next with the exact conflict
evidence so the workflow command explains the routing, but do not tell it to ignore that conflict.
End that PR with CLAIM_CONFLICT and make no workflow-state, branch, worktree, Issue, PR, label, or
marker mutation.

In every review path, inspect the full PR, linked Issues and ownership, diff, comments, checks,
merge state, local validation evidence, documentation, and fresh remote state. Do not merge based
only on MERGEABLE or green prose. Ignoring an origin-handoff refusal means only that review may
continue; it never means the claim succeeded. Never synthesize a replacement state file, adopt the
author run, clear its claim, or change the sink from PR to merge.

For the unclaimed path, when every mission item is complete, use kaola-workflow-finalize for final
validation, documentation docking, Issue closure, archive, sink, final commit/push, merge, and
fetched-live verification. For ORIGIN_PR_HANDOFF, the authoring run already finalized to a PR sink;
after a clean review, merge and let `watch-pr` settle that original run. Never force-push, bypass
gates, invent Issues, reorganize the backlog, or touch
unrelated, dirty, protected, human-owned, active, or unclear work. If a material human decision is
required, print HUMAN_DECISION_REQUIRED with the exact decision and options here, pause the affected
work, and prevent later firings from duplicating it. End after all currently actionable PRs are
finalized or no safe progress remains. Before terminal shutdown prove PR merged state, linked Issue
terminal state, zero matching kw:claim markers and workflow:in-progress labels, zero Runner
schedulers/detached intake, a clean aligned repository, and the agreed exact tmux disposition;
every later firing re-queries GitHub from scratch.
```
