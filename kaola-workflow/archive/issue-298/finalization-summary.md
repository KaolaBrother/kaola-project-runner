# Finalization summary — issue-298

## Delivered

Fix for #298: a Host-only `state retire --kind decisions --id X --absent
--evidence E [--outcome R]` that records a citable closure receipt for an
owner decision that never had a decision row, per the owner's storage
decision (option A, issue comment 2026-10-09).

- `scripts/kaola-dispatch.py`:
  - `retire_absent_decision`: decisions-only, Host-writer-only; refuses a
    current `decisions/X` (recovery names the normal retire), refuses
    `--expect-rev/--handoff/--cite/--index/--live`, requires `--evidence`;
    returns `{kind, id, outcome, absent_at_retire: true, evidence, at,
    host_revision}` — `host_revision` rises like any Host business write
    and the receipt cites it. The file stores no row, stone, or tombstone,
    and no decision row is created.
  - `record_recovery` absent-case text now names the `--absent` command as
    the route for owner closures that never had a decision row.
  - The normal retire path gained a named `expect-rev-required` refusal
    (previously surfaced as a `conflict` with a null revision).
- Docs: `docs/api.md`; `templates/orchestrator/references/lifecycle-state.md`
  and `sideagent-node.md` updated through the template sources with
  regenerated skill copies; CHANGELOG Unreleased entry (dispatch CLI +
  shipped reference copy; seats restart not required).
- Tests: `tests/contract/test-issue-298-absent-decision-retire.py` (7
  cases): absent id returns a citable receipt and stores nothing;
  `retired:decisions/X` checkpoint acceptance for an absent row kept;
  `--absent` on a current decision refused; without `--absent` the refusal
  stays `record-missing` with the file unchanged; sideagent/tool writers
  refused; decisions-only and flag rejection; docs name the receipt.
  Registered in `validate.sh`.

## Candidate

- Implementation commit `f6ce0e12` on `workflow/issue-298` (worktree
  `.kw/worktrees/issue-298`, base `c8a99238` = main). Implemented by the
  `grok/default` seat `grok-KPR-i298-absent-retire`; reviewed and
  finalized by the Host.

## Evidence

- Host diff review (this run): receipt shape, no-storage guarantee, writer
  and kind restrictions, and default-path preservation verified
  path-by-path.
- `./scripts/render-skills.py --check` — PASS.
- Affected suites, all exit 0: `test-issue-298-absent-decision-retire.py`
  (new), `test-issue-255-lifecycle-state.py` (byte-identical default-refusal
  test kept green), `test-issue-271-dispatch-help.py`, `test-ddd-pack.py`,
  `test-issue-244-dispatch.py`, `test-issue-292-state-record-root.py`
  (logs `/tmp/kpr-i298-*.log`).
- `.cache/final-validation.md`: verdict `pass`, candidate hash
  `45f9186860078eb1…`.
- Worker seat exact-stopped after acceptance (`state: stopped`).

## Known failures / unverified scope

- Full inventory and per-platform live ACP smoke run immediately next at
  the v0.9.4 release boundary over the integrated candidate, per the run
  plan.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- scripts/kaola-dispatch.py
- scripts/validate.sh
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/lifecycle-state.md
- skills/kaola-project-runner/references/sideagent-node.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/references/lifecycle-state.md
- templates/orchestrator/references/sideagent-node.md
- tests/contract/test-issue-298-absent-decision-retire.py

## Follow-Up Items

- None. The v0.9.4 release is the remaining run step.

## Final readiness

Ready: candidate reviewed, affected scope green, validation recorded.
Proceed to sink (merge) and archive.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-298/finalization-summary.md
