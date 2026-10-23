# Finalization Summary — Issue #407

## Delivered

Fixed KPR #407 on `workflow/issue-407`: the issue-306 bytecode fixture is now a
real Git checkout, so `render-skills.py --check` pin verification runs honestly
in the post-release pinned window instead of refusing a non-Git tree copy.

- Decision **(b)** of the two offered directions. Basis: `pin_findings` proves
  Git-history facts (accepted commit exists, ancestor of `HEAD`,
  `required_pin_paths` present, P−R delta limited to the four pin files) that are
  only meaningful in a checkout, and the issue-49 contract test
  `test_pinned_stage_cannot_be_verified_outside_a_git_checkout` locks the
  behavior that a pinned stage on a non-Git tree must fail `--check` and
  `--write` — "an unverifiable pin is never written". Option (a) would have
  weakened that locked contract.
- `tests/contract/test-issue-306-bytecode-payload.py` only; the product
  (`scripts/render-skills.py`, templates, generated surfaces) is untouched. The
  fixture follows the file's own `git_repo()`/`set_stage()` precedent: copy →
  reset to content stage → `--write` → `git init`/commit → R → flip
  `accepted-revision.json` to `pinned` naming R → `--write` → commit → P.
- Both pin stages are exercised end to end in one test: `--check` PASS at
  content stage, then `--check`/`--verify-install`/`install-local.sh` and the
  real-extra-file rejection at the pinned stage, with bytecode planted per
  stage (`--write` regenerates skill dirs wholesale). Git fixture calls carry
  the Issue #80 `maintenance.auto=false` hardening.

Candidate: `3cad4e496ff95aaca463a43de2d4fc8f17025b0d` on `workflow/issue-407`;
parent `5c8551ee`. No tag, release, install, or amplification of the change was
performed.

## Acceptance Evidence

- Host verdict: ACCEPTED — independent review PASS (mutation probes verified
  the fixture genuinely enforces ancestry and the P−R delta; no weakened
  assertions; product untouched) plus Host verification (pinned-window demo
  rerun green).
- Original reproduction: historical bisect
  `/tmp/kpr-405-repro/standalone-306-at-{R,P}.log`,
  `fullgate-main-22814695-run1.log`; forward probe `/tmp/kpr-407-repro/`.
- Fix receipts under `/tmp/kpr-407-fix/`: `pin-demo-render-write.log`,
  `pin-demo-render-check.log` (simulated pin on the candidate worktree,
  `commit=3cad4e49`, label `repro-only pin window probe`, pin verified),
  `pin-demo-306-suite.log` (the suite green inside that simulated pinned
  window), `fullgate.log` (full inventory).

## Validation

## Changed Paths

## Documentation Docking

None required — the change is test-only; no user-visible surface, API,
convention, or generated product changed.

## Follow-Up Items

- None filed; the defect class is closed by this fix. Future release pin
  commits will recreate the pinned window; the suite is now green in it.

Final readiness: ready. Merge sink to `main`, close #407 with the evidence
summary, archive the run, and remove the run worktree and branch. No release,
tag, or install.
