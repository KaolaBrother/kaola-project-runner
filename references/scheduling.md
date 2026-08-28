# Optional scheduling

Read this reference only when the user explicitly requests periodic, recurring, or delayed work.
Scheduling changes when work runs; it does not replace the project-run contract.

This file describes recurring execution inside Grok. It is separate from the mandatory 15-minute
Codex supervision heartbeat in [codex-supervision.md](codex-supervision.md).

## Main-conversation requirement

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
- classify linked-Issue claims before any PR claim attempt;
- use `workflow-next` for an unclaimed explicitly authorized target, never to take over an origin PR
  handoff or a foreign claim;
- surface `HUMAN_DECISION_REQUIRED` in the same main conversation and stop that firing;
- use `kaola-workflow-finalize` only after the mission frontier is complete;
- perform no work when the scheduled condition is false;
- never auto-route to an unrelated next issue.

When the condition is a PR intake, the scheduled prompt should carry the versioned marker
`MAIN_THREAD_PR_INTAKE_V2_CLAIM_SAFE`, query fresh forge truth on every firing, process an authorized
PR set in a deterministic order, and say `NO_OPEN_PRS` without repository or Issue mutations when
none exist.
It uses `workflow-next` and `kaola-workflow-finalize` only when the selected PR has no active linked-
Issue claim. An origin PR handoff uses non-claiming review, merge, and `watch-pr`; a foreign or
ambiguous claim is skipped without local or remote workflow mutation.

## Verification

After creation, verify from live evidence:

- the scheduler identifier and intended interval;
- `foreground: true` from the creation call or authoritative scheduler detail, not prompt echo;
- exactly the intended scheduler count for this project;
- zero detached General-loop schedulers and zero detached project-intake subagents;
- a real firing appears as a new turn of the same Grok session;
- disabling or stopping it affects no other scheduler or tmux session.

If periodic work was not requested, create no scheduler at all.

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
Targets: {explicit issue set or workflow-next selection boundary}
Definition of done: {validation and lifecycle evidence}
Authority boundary: {authorized mutations and user decisions}

Read fresh repository, forge, and Kaola Workflow state. Resume an active workflow before taking
anything new. Use workflow-next only inside this goal and scope. Keep mission-list.md as the
recovery record and this main conversation as the owner. If a material user decision is required,
print HUMAN_DECISION_REQUIRED with the exact decision, evidence, recommendation, and options here,
pause the affected run, and prevent later firings from duplicating it. When every mission is done,
use kaola-workflow-finalize and verify validation, sink, remote state, Issue state, archive, and
cleanup. Do not invent work or move beyond the authorized goal.
```

## PR review loop template

This is the reusable form of the tested PR Automation contract:

```text
MAIN_THREAD_PR_INTAKE_V2_CLAIM_SAFE: Query fresh GitHub truth for open pull requests in {owner/repo} using gh pr
list --repo {owner/repo} --state open --limit 100 --json
number,url,title,isDraft,headRefName,baseRefName,updatedAt. This firing is a new turn in the same Grok
main conversation; never hand intake to a detached General loop or detached subagent.

If the result is empty, make no repository, Issue, roadmap, branch, or worktree changes and end this
turn with NO_OPEN_PRS. Process non-draft open PRs one at a time in ascending PR number. Before any
workflow startup, fetch the PR head/base and linked Issues, then inspect every linked Issue's
`workflow:in-progress` label and `kw:claim project=...` marker.

Classify the PR using the pr-claim-handoff contract. If no linked Issue has an active claim, use
workflow-next to review PR #{number}, passing its exact number and URL and making complete review
part of the mission; after every mission item is done, use kaola-workflow-finalize. If every linked
Issue is claimed by one project and the PR head is that project's authoring branch, classify
ORIGIN_PR_HANDOFF: do not call startup/workflow-next, do not reconstruct or adopt its workflow
folder, and do not run kaola-workflow-finalize a second time. Review the frozen PR candidate without
taking the claim; if clean, merge the PR and run the existing author's watch-pr cleanup only when
its exact local state is available. If the claim belongs to another project/branch, claims differ
across the bundle, or ownership is uncertain, end that PR with CLAIM_CONFLICT and make no workflow,
branch, worktree, Issue, or PR mutation.

In every review path, inspect the full PR, linked Issues and ownership, diff, comments, checks,
merge state, local validation evidence, documentation, and fresh remote state. Do not merge based
only on MERGEABLE or green prose. Never bypass a refused claim by working offline, synthesizing a
replacement state file, or changing the sink from PR to merge.

For the unclaimed path, when every mission item is complete, use kaola-workflow-finalize for final
validation, documentation docking, Issue closure, archive, sink, final commit/push, merge, and
fetched-live verification. For ORIGIN_PR_HANDOFF, the authoring run already finalized to a PR sink;
after a clean review, merge and let `watch-pr` settle that original run. Never force-push, bypass
gates, invent Issues, reorganize the backlog, or touch
unrelated, dirty, protected, human-owned, active, or unclear work. If a material human decision is
required, print HUMAN_DECISION_REQUIRED with the exact decision and options here, pause the affected
work, and prevent later firings from duplicating it. End after all currently actionable PRs are
finalized or no safe progress remains; every later firing re-queries GitHub from scratch.
```
