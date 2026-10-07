# Finalization summary — issue 283

## Delivered

Phase 4 of the optional DDD component (design `kaola-ddd/1` revision 2, `8b3779c9`). Docs only;
no change to templates, skills, scripts or suites. Candidate: `c3a0e4f7` on `workflow/issue-283`,
rebased onto `origin/main` `60e9e717`.

- `docs/ddd/packs/c1-exact-stop.md`: the second `kaola-ddd-pack/1` pack. Work unit: exact-stop a
  seat. `context_primary` is `session-runtime/C1-lifecycle`. It crosses CORE-identity, C3-events,
  C6-recovery and C4-state, and each crossed boundary has its own contract bullet. Citations are
  at `4c30b71d`. New measured gaps S1–S3 are tracked in #289. The pilot's G9 was re-measured.
- `docs/ddd/host-usage-decision.md`: the decision is no orchestrator template change this round.
  It records the evidence, the exact proposed text with its byte-budget impact (+317 B to
  `references/doc-maintenance.md`), the re-open criterion, and the Host comparison
  (#281 with a pack vs #278 without a pack). That comparison establishes no measurable benefit or
  cost of citing a pack.
- `docs/ddd/README.md`, `docs/ddd/context-map.md`: index rows, uninstall note, session-runtime
  evidence.

## Acceptance

Host verdict: **ACCEPTED** on `8c94c3a4`, with one requested doc addition (Host message,
2026-10-07). The Host spot-checked `op_or_holder_lost` (`A:1868-1877`) and
`force_kill_from_record` (`A:2230`) against the S1/S2 description. The requested addition is in
`b6e7c156`, rebased as `c3a0e4f7`: the Host comparison section and the #289 references.

The checker-integration sub-item is not applicable: there is no checker on `main` yet (#282). Per
the #283 acceptance terms, it never blocks #283.

Evidence locations:

- this run's `.cache/final-validation.md`;
- the pack's `## Evidence` section;
- the decision document.

## Validation

classification: final_validation_stale
green: false
mode: final-validation

recorded validated_candidate_hash "c9854753b28057a72904a58175b332579eb5de463dc63c769d2d82288a6906a0" != current code-tree hash "a3c6bedaa7a5596624c03c8e98854c4de6b7bd0d8aa63b4848927672d4158cec" — a relevant source/test/test-consumed file changed after the recorded validation; re-run the validation command and re-record final-validation.md with a fresh hash

A relevant source/test/test-consumed file changed after validation — or the record was written from a different checkout than this one. Re-run the validation command, then re-record with `kaola-workflow-validation-runner.js record --project <project> --verdict pass --command "<the validation command you ran>"`, invoked from the working tree you validated (the gate hashes the tree its own shell is in, and a linked worktree and main differ until the branch merges); never hand-patch the hash.

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- docs/ddd/README.md
- docs/ddd/context-map.md
- docs/ddd/host-usage-decision.md
- docs/ddd/packs/c1-exact-stop.md

## Known failures and unverified scope

- `./scripts/render-skills.py --check` exits 1 on `main` and on this candidate. Every finding is a
  `pin:` line from the stale Grok Bot pin `3de9f61afbfa`. It is pre-existing and was not fixed;
  the pin is a protected path. For the same reason, `validate.sh --suite` stops at its
  render-check preamble. The cited suites were therefore run directly in a sandboxed environment
  that mirrors validate.sh (commands in `final-validation.md`).
- `test-issue-50-runner-integration.py` result: 6/7. The one failure is
  `test_manifest_and_generated_skill`, which asserts that `--check` passes (the same pin finding).
- `test-issue-266-launch-broker-composed.py` is cited from reading only and was not re-run.
- The pack is accepted by Host review. No mechanical checker verified it.
- The `## Validation` classification `final_validation_stale` above has a known cause. The
  finalize transaction mirrored the main checkout's pre-existing protected changes
  (`hosts/grok-bot/*`, `templates/grok-bot/accepted-revision.json`) into the worktree and into its
  `chore: finalize` commit `2634498e`. That changed the code-tree hash. The commit was never
  pushed, and it was dropped under the Host's pre-authorized recovery (reset to `c3a0e4f7`). The
  recorded validation binds `c3a0e4f7`'s tree, and that is the tree published, with the
  archive-only commit added on top.

## Follow-Up Items

- #289, filed by the Host: S1–S3 from the second pack. S1: a dead-holder stop skips the
  expected-instance check. S2: it sweeps without `--force`. S3: the `holder_instance_mismatch`
  event is not asserted. No new issue is filed by this run.
- #286 (also pack-cited) is still in flight and is not included in the comparison. Re-open the
  template decision only under the recorded criterion.

## Readiness

Ready for archive and the merge sink.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-codex-160-live-2026-10-03.md
- docs/harness-acp-compat-2026-10-01.md
- docs/harness-acp-compat-2026-10-03.md
- docs/harness-acp-compat-2026-10-06.md
- docs/harness-acp-reverify-2026-10-01.md

