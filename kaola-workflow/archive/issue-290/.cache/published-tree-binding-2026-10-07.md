# #290 published-tree binding note — post-archive supplement (2026-10-07)

Recorded by Host `zcode-KPR-orchestrator-main` (holder `eb9f120438d48c82131ada5bc1e56919`),
matching the #289 convention (`4db4c851`) and #287 (`6d9fdc1c`).

The archived `finalization-summary.md` `## Validation` section carries the
transaction-time snapshot `final_validation_stale / green: false`. Two external
causes, both reported by the finalizing agent: (a) the finalize transaction's
transient residue mirror (the standing protected-dirty-files effect); (b) the
sink's rebase onto a main that had absorbed #289's `scripts/kaola-acp.py` and
CHANGELOG changes, so the published tree legitimately differs from the
recorded candidate tree. Per the finalize Skill, an archived record is closed
evidence — nothing was hand-edited or re-recorded.

The canonical record `.cache/final-validation.md` stands:
`verdict: pass`, `validated_candidate_hash
39311095b02352c1621792a7942ef76ef4991c514f7063e17b4c0ccb7f1db115`, command =
`./scripts/validate.sh --suite test-issue-286-retire-input.py --suite
test-issue-244-dispatch.py --suite test-issue-271-dispatch-help.py`.

Host acceptance evidence (2026-10-07, independently re-run in an unrestricted
shell at the candidate worktree): test-issue-286-retire-input Ran 19 OK,
test-issue-244-dispatch Ran 79 OK, test-issue-271-dispatch-help Ran 1 OK,
render `--check` PASS under the worktree-only content-stage flip; worktree
restored clean. Published: fix `15249ad7`, sink/archive `414bde99`, issue
#290 CLOSED by merge sink.
