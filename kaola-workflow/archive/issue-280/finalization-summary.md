# Finalization summary — issue 280

## Delivered

Phase 1 of the optional DDD component, following design `kaola-ddd/1` revision 2 at
`8b3779c9c9c76e03f6794b5bf5cf6ffb76bd27c0`. Documentation only; no code, template or suite change.
Candidate: `ab8e63fca68742b6af5be76ed504d5941171fdc7` on `workflow/issue-280`.

- `docs/ddd/README.md` — the pack schema `kaola-ddd-pack/1`, covering:
  - the `context_primary` and `contexts_touched` keys;
  - `owner` as content responsibility only;
  - the forbidden authority keys;
  - the eight fixed sections.

  It also covers how to write a pack, the simplified path, a default uninstall that keeps current
  documents, the advisory-only scope of checks, and the pilot findings for each candidate check
  in design §2.3.
- `docs/ddd/context-map.md` — `kaola-ddd-map/1`. Every grouping is labelled `candidate`, with its
  evidence and its open question. Q3 result: C4 (state) and C5 (dispatch) share one language and
  form two consistency boundaries.
- `docs/ddd/packs/c4-state-retire.md` — the pilot pack, a cross-component sample: C4 state, C5
  dispatch index and C1 session lifecycle. Every seam names either its suite or a measured gap
  (G1–G9).

## Acceptance

Host verdict: **ACCEPTED** on `ab8e63fc` (Host message, 2026-10-07). The Host verified:

- the pack is based on design revision 2 (`8b3779c9`);
- the candidate is docs-only (3 files);
- `context_primary`/`contexts_touched` and the C4/C5/C1 sample are present;
- the owner, uninstall and advisory wording matches revision 2;
- every cited suite exists in `validate.sh --list`;
- spot-checked citations are accurate: `D:3546`, `4997`, `5003`, `4913`, `4906`, `5171`;
- G1–G3 are confirmed absent from the tests;
- the Q3 evidence is sound.

The only non-existent paths are the phase-3 checker files named in the README uninstall
section. The Host accepted them as future items.

Evidence locations:

- this run's records (`.cache/final-validation.md`);
- the pack's `## Evidence` section;
- the README `## Pilot findings` section.

## Validation

classification: final_validation_stale
green: false
mode: final-validation

recorded validated_candidate_hash "5ae3531e7a70461d7bca316b964bbaddf67c5ce1d0b84db47632075cbf218147" != current code-tree hash "6d86f853083bfcf5bd9ee3436da5728b25b64999bf888db6eedb6ea9b05e40b9" — a relevant source/test/test-consumed file changed after the recorded validation; re-run the validation command and re-record final-validation.md with a fresh hash

A relevant source/test/test-consumed file changed after validation — or the record was written from a different checkout than this one. Re-run the validation command, then re-record with `kaola-workflow-validation-runner.js record --project <project> --verdict pass --command "<the validation command you ran>"`, invoked from the working tree you validated (the gate hashes the tree its own shell is in, and a linked worktree and main differ until the branch merges); never hand-patch the hash.

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- docs/ddd/README.md
- docs/ddd/context-map.md
- docs/ddd/packs/c4-state-retire.md

## Known limitations

- `./scripts/render-skills.py --check` exits 1, but this is pre-existing and unrelated to this
  change. At base `8b3779c9` it printed 85 `pin: P may differ from 3de9f61afbfa …` lines. At
  `ab8e63fc` the output is the same 85 lines plus 3 more, one per new `docs/ddd` file. The stale
  Grok Bot pin belongs to the protected `templates/grok-bot/accepted-revision.json`, which this
  run did not touch.
- G5, G6 and G9 were found by scratch-directory probes, not executed by any suite. Whether they
  are defects is a Host judgment.
- Change coupling between C4 and C5 was not measured (Q3). C6 was examined only at its two
  retire seams.

## Follow-Up Items

- G1–G9 (pack `## Dependency contracts`) are input to #281 (contract fixtures) and #282
  (checker decision).
- G5, G6 and G9 are measured behaviour and may be defects. The Host is filing them as a separate
  A-line defect issue, so this run files none.

## Readiness

Ready to sink: merge `workflow/issue-280` into `main`, push, and close #280.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-codex-160-live-2026-10-03.md
- docs/harness-acp-compat-2026-10-01.md
- docs/harness-acp-compat-2026-10-03.md
- docs/harness-acp-compat-2026-10-06.md
- docs/harness-acp-reverify-2026-10-01.md

