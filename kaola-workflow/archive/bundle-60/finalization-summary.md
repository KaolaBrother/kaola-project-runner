# Finalization Summary — Issue #60

project: bundle-60
branch: workflow/bundle-60
sink: merge
candidate: 555bfb8 (workflow/bundle-60, 1 commit over base 7a2e8bd, clean worktree)

## Delivered

Issue #60 fixes the claude-code markdown-inventory RED in `tests/contract/test-lifecycle-contract.py`.
Root cause: the renderer ships four vendored bridge files into the generated claude-code worker
package (`scripts/render-skills.py` `VENDORED_BRIDGE_FILES`), including the provenance doc
`UPSTREAM.md`; the lifecycle inventory check expects only the four standard Markdown files, so the
package's extra `scripts/vendor/claude-code-acp/UPSTREAM.md` tripped the check on every run.

Fix (user decision: remove it from the package): drop `"UPSTREAM.md"` from the renderer's ship set
and from the mirror tuple in `tests/contract/test-issue-50-runner-integration.py`, then regenerate.
The generated claude-code package now carries only what runtime needs (`dist/index.js`, `LICENSE`).
The repo-root provenance record `vendor/claude-code-acp/UPSTREAM.md` is kept — it is the vendoring
source and the `test-issue-50-claude-acp-bridge.py` provenance test reads it from there. The
lifecycle inventory check passes with all nine worker packages.

## Files Changed

Commit on `workflow/bundle-60` over base 7a2e8bd (carries the factory-droid co-author trailer):

- `555bfb8` fix(render): stop shipping the vendored claude-code-acp UPSTREAM.md in the generated skill (3 files, +2/−81)

Changed file list (from `git show --stat`):
- `scripts/render-skills.py` — `VENDORED_BRIDGE_FILES` drops `"UPSTREAM.md"`.
- `tests/contract/test-issue-50-runner-integration.py` — `VENDORED_FILES` mirror drops it.
- `skills/claude-code-kaola-project-runner/scripts/vendor/claude-code-acp/UPSTREAM.md` — deleted by regeneration.

## Test Coverage

- `./scripts/validate.sh` on the frozen candidate: **exit 0** (`VALIDATE_EXIT=0`, worker-run full suite on the frozen worktree: render-skills PASS, per-skill validate-skill PASS, installer suites PASS, all contract suites OK incl. issue-50-claude-acp-bridge provenance, issue-50-runner-integration 7/7 with 181 checks, issue-51-runner-integration 6/6 with 119 checks; the 181 vs 182 check delta mirrors the dropped tuple element and is expected).
- `python3 tests/contract/test-lifecycle-contract.py` (the test this issue exists for): exit 0, "communication lifecycle acceptance: PASS" — the claude-code inventory RED is gone; all nine worker packages pass.
- `./scripts/render-skills.py --check`: PASS (worker + orchestrator re-verification; budgets OK).
- `git diff --check`: clean.
- Orchestrator re-verification first-hand: commit diff reviewed (only the two tuples + generated deletion), lifecycle test + render --check PASS on the frozen worktree, worktree clean at 555bfb8.

Validation-environment note (not a product defect): an orchestrator-triggered redundant background
re-run of `./scripts/validate.sh` stalled ~15 min into its acp-watch/install-local branch with no
suite failure; it was killed, and orphaned mock-agent/holder leftovers from my earlier bundle-58/59
runs were cleaned up (zero `bundle-5[89]` residue after cleanup; two unrelated `~/.codex` processes
left untouched). The worker's completed full run on the same frozen tree is the acceptance evidence
used for this receipt.

## Validation

- `.cache/final-validation.md`: `verdict: pass`, command `./scripts/validate.sh`, `validated_candidate_hash: 0327b38f0d5276b8e7de7a834a54a19b14532cedb683e7ad35ca53d4da1e9171` (frozen candidate 555bfb8; worker full run `VALIDATE_EXIT=0`; orchestrator quick gates PASS).
- Acceptance legs: automated (validate.sh + render --check + lifecycle contract) — executed, pass; live/local/manual — none required (packaging-internal change with no runtime surface).
- Issue walk: issue #60's requirement (normalize the claude-code markdown inventory so the report is clean) is satisfied — the "normalize the inventory expectation" option plus the package no longer shipping the doc. The repo-root provenance file remains, so the issue's alternative (drop from package only if not meant to ship) is also consistent: the doc stays as the vendoring record, just not inside the generated package. The comment on #60 will record the outcome for the record.

## Changed Paths

Per the finalize transaction report (read-only check): the three files listed above (renderer,
generated package deletion, test mirror). The transaction's appended findings below carry the
authoritative list.

## Documentation Docking

`.cache/doc-docking.md` → **DOCKED** (no-impact verified: no docs enumerate the vendored bridge
file set; runtime surface unchanged; repo-root provenance record untouched).

## Follow-Up Items

- None filed. The validation-environment stall was investigated: it produced no product failure and
  the acceptance evidence stands on the worker's completed frozen-candidate run. Orphaned test-agent
  cleanup is mentioned in the mission result for the record.
- Pre-existing state: `test-lifecycle-contract.py` is green again for all nine workers (this run's
  whole purpose); nothing else deferred.

## Closure Decision

Issue set: #60 only. All acceptance parts are satisfied (see Validation and the issue walk). Close
#60 on Workflow sink. No keep-open. After the sink, cut the v0.3.3 release (tag + GitHub release),
per the user's standing instruction — the 0.3.3 changelog was prepared in the #58 run; this fix is a
maintenance item in that release window.

## Readiness

READY_FOR_FINALIZE — pending the finalize transaction, merge sink, v0.3.3 release, and closure audit.

## Sink Findings

(File from finalize transaction.)

archived_paths:
- kaola-workflow/archive/bundle-60/.cache/doc-docking.md
- kaola-workflow/archive/bundle-60/.cache/final-validation.md
- kaola-workflow/archive/bundle-60/.cache/mirror-digest.json
- kaola-workflow/archive/bundle-60/.cache/origin/selection-record.json
- kaola-workflow/archive/bundle-60/finalization-summary.md
- kaola-workflow/archive/bundle-60/mission-list.md
- kaola-workflow/archive/bundle-60/workflow-state.md
