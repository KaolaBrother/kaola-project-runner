# Documentation Docking — issue-83

verdict: DOCKED

Changed public behavior: `scripts/validate.sh` lane/replay reporting. A failing
suite no longer aborts its lane — every suite runs and is measured; the ordered
replay prints `SKIPPED: <suite> (no log; execution status unknown)` for a suite
that left no log instead of dying on a `cat: No such file or directory` error;
overall nonzero exit on any failure; green-path output unchanged.

Checked files:

- `README.md` — Validation and evidence section (README.md:400-410) lists only
  `./scripts/render-skills.py --check` and `./scripts/validate.sh` as commands;
  no lane/replay prose. No impact.
- `docs/conventions.md` — mentions `./scripts/validate.sh` only as the
  after-change command (conventions.md:50). No impact.
- `docs/architecture.md`, `docs/api.md` — no validate-lane behavior described.
  No impact.
- `docs/runner-v2-dual-transport-design.md` — historical design doc; references
  validate.sh as a command only. No impact.
- `AGENTS.md` — Commands/Validation Policy list `validate.sh` by name only;
  no behavior detail to update. No impact.
- `CHANGELOG.md` — house convention records user-visible fixes under
  `## Unreleased`. FIX APPLIED: entry added describing the lane-abort defect,
  the FAILED-per-suite + SKIPPED reporting contract, and the covering test.
  The 0.3.5 lane-parallelism entry and Issue #80 entry stay as history.
- `tests/contract/test-issue-49-grok-bot-host.py` stale-string sweep covers
  CHANGELOG.md — new entry introduces none of its forbidden strings
  (verified by suite pass during full validate at af3af6e; the changelog
  delta itself contains none).

Evidence: `kaola-workflow/issue-83/evidence/` — validate-green.log,
validate-failure-path.log, focused-test-postfix.log, commit diffs.
