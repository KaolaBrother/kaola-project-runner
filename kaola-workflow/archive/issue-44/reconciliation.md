# Issue #44 first finalization outcome

The first `issue-44` run did not establish merge readiness. During finalize, its residue mirror copied an unrelated, uncommitted consumer-specific edit from the main checkout into `skills/kaola-project-runner/SKILL.md` on `workflow/issue-44`. The tool reported `final_validation_stale` because the code-tree hash changed after the recorded PASS. That branch was not published or accepted.

The uncommitted edit was preserved outside the repository before restoring the main generated file; the authoritative project-specific authorization and heartbeat records remain in the consuming VRPAI project. A fresh `pr-45-review-2` run started from exact PR #45 head `d717ffedeb04c9189d3792268eb10129de210fcf`, reran validation, and produced a green finalization receipt. This archive is retained as failure evidence.
