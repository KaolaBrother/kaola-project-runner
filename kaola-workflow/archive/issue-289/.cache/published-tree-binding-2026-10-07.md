# #289 published-tree binding note — post-archive supplement (2026-10-07)

Recorded by Host `zcode-KPR-orchestrator-main` (holder `eb9f120438d48c82131ada5bc1e56919`),
matching the #287 supplement convention (`6d9fdc1c`).

The archived `finalization-summary.md` `## Validation` section carries the
transaction-time snapshot `final_validation_stale / green: false`
(`1c3dd7bd… != 5ec1e3ad…`). Cause: the finalize transaction's residue mirror
had copied main's dirty protected owner files into the tree at transaction
time, so the gate then measured the dirty-mirror code-tree `5ec1e3ad…`. The
finalizing agent dropped that mirrors-only `chore: finalize` commit
(`git reset --hard 9b206a30`) before the sink — nothing was published
(precedent 774ff7a6).

The canonical record `.cache/final-validation.md` is correct and binding:
`verdict: pass`, `validated_candidate_hash 1c3dd7bd379844e2e8c5ad51603707cc5cc3989c05effe9bc56c923a5935f62e`,
command bound to candidate `9b206a30` (rebased onto `836bc41c`). The
published clean tree at merge `48ef4d25` / fix `9b206a30` hashes to exactly
`1c3dd7bd…` (verified in an isolated worktree by the finalizing agent; sink
reported `invalidated_evidence: []`).

This note edits nothing retroactively; the stale summary snapshot stands as
transaction-time evidence of the mirror effect. Host acceptance evidence:
`test-issue-289-dead-holder-stop.py` Ran 6 OK, `test-acp-contract.py`
Ran 85 OK, `test-generated-skills.py` PASS (2026-10-07, content-stage flip,
worktree restored clean).
