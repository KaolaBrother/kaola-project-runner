# Kaola Workflow lifecycle

This runner integrates with the installed Kaola Workflow skills; it does not replace their detailed
contracts. Claude Code must read the currently discovered `workflow-next` and
`kaola-workflow-finalize` instructions when each phase begins.

## Start or resume with workflow-next

The main conversation must:

1. for project work, pass goal context without narrowing selection to one Issue and let
   `workflow-next` select the most appropriate coherent batch; for PR mode, honor the exact PR as
   the review object without instructing it to claim one linked Issue;
2. refresh local and remote truth before claiming;
3. resume an existing active folder only when this conversation is its verified owner or successor;
   another session's folder, branch, worktree, and Issues remain untouched;
4. create or maintain `kaola-workflow/{project}/workflow-state.md`;
5. write `kaola-workflow/{project}/mission-list.md` immediately after a new claim;
6. treat the mission list as the single recovery index and preserve completed item results;
7. stop for user consent on irreversible or value-laden decisions.

Mission items are outcome-sized. A detached worker can own one bounded item, but the Claude Code main
conversation keeps run synthesis and user decisions.

For PR review, an active claim can be the authoring run's intentional PR-sink footprint. Apply
[pr-claim-handoff.md](pr-claim-handoff.md), then invoke `workflow-next` with that explanation. For a
verified authoring PR handoff, a refused claim is ignored only as a blocker to continuing the PR
review; it remains authoritative proof that the reviewer did not acquire the Issues or author run.
Never reconstruct or adopt the other run to manufacture ownership.

## Finalize only after the mission frontier is complete

The main conversation invokes `kaola-workflow-finalize` only when every mission item is done. It
then owns:

- final validation bound to the candidate actually being published;
- acceptance against every claimed issue;
- documentation update and docking;
- run-gap classification and follow-up issue handling;
- the whole-run close or agreed keep-open decision;
- finalize transaction, sink, archive, remote proof, and closure audit.

Do not treat a green CI badge, a mergeable flag, a PR merge, or a success message as the whole
completion contract. Read the emitted evidence and verify fetched-live state.

For a merged PR, cleanup of completed linked Issues is part of the Project Runner lifecycle. Prefer
the exact originating run's installed `watch-pr` when its local state exists. If origin state is
absent or `watch-pr` cannot settle cleanup, prove merge plus terminal Issue mapping and remove only
the matching origin claim marker(s) and `workflow:in-progress` label(s). Never touch foreign or
mismatched claims or open unfinished Issues; use `HUMAN_DECISION_REQUIRED` when ownership or
completion is ambiguous. A PR run is not terminal while matching claim residue remains.

After the selected batch is closed and archived, or the agreed keep-open terminal state is recorded
and sunk, stop. One-shot completion does not authorize starting a second unrelated batch; recurring
project mode may let `workflow-next` select the next batch on a later authorized firing.
