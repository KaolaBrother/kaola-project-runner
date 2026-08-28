# Kaola Workflow lifecycle

This runner integrates with the installed Kaola Workflow skills; it does not replace their detailed
contracts. Grok must read the currently discovered `workflow-next` and
`kaola-workflow-finalize` instructions when each phase begins.

## Start or resume with workflow-next

The main conversation must:

1. honor a user-named issue or PR;
2. refresh local and remote truth before claiming;
3. resume an existing active folder for the target instead of claiming twice;
4. create or maintain `kaola-workflow/{project}/workflow-state.md`;
5. write `kaola-workflow/{project}/mission-list.md` immediately after a new claim;
6. treat the mission list as the single recovery index and preserve completed item results;
7. stop for user consent on irreversible or value-laden decisions.

Mission items are outcome-sized. A detached worker can own one bounded item, but the Grok main
conversation keeps run synthesis and user decisions.

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

After the selected issue set is closed and archived, or the agreed keep-open terminal state is
recorded and sunk, stop. A completion never authorizes automatically selecting the next issue.
