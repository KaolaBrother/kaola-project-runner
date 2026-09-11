# Deliver Runner v2 dual transport and verify it across supported platforms

1.
   item: Define focused acceptance coverage for manifest/template transport facts, runtime dispatch and schema v3, packaging, and cross-transport duplicate detection.
   status: done
   dispatched: self — acceptance changes will land in tests/contract/ in the claimed worktree
   result: tests/contract/test-runner-v2.py added; baseline run failed 3 tests and errored 1, proving the requested surfaces are absent

2.
   item: Implement issues #19, #20, and #18 as one cohesive dual-transport production surface, render generated Skills, and update API/architecture documentation.
   status: done
   dispatched: self — production, generated, and documentation changes will land in the claimed worktree
   result: manifest/template/runtime/holder/observation/docs changes landed in the claimed worktree; generated six Skills; focused Runner v2 tests 4/4 PASS, ACP contract 13/13 PASS, validate.sh PASS

3.
   item: Execute issue #21 live ACP verification on Cursor, Devin, OpenCode, and Claude plus the Kimi permission probe, preserving exact receipts and docking measured platform facts.
   status: done
   dispatched: self — receipts will land under kaola-workflow/bundle-18-19-20-21/evidence/ and findings in docs/
   result: docs/acp-live-verification-2026-09-11.md and evidence receipts landed; Cursor/Devin/OpenCode scenarios 1/3/4/7 PASS, Kimi plan-mode permission and permit PASS, Claude wrapper objectively returned probe-eof before initialize; cross-transport duplicate warning reproduced

4.
   item: Validate and independently inspect the exact candidate against all four issue acceptance criteria, repairing any defects until it is ready for finalization.
   status: done
   dispatched: self — final diffs and verification output will be inspected in the claimed worktree
   result: render check PASS; validate.sh PASS including 13 ACP, 4 Runner v2, and generated Skill acceptance; git diff --check clean; frozen templates/grok-golden diff empty; all run-created sessions stopped
