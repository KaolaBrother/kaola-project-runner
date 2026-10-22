# Finalization Summary — Issue #402

## Delivered

Aligned the time-bound CHANGELOG assertion in
`tests/contract/test-issue-349-checkpoint-verb.py` with the shipped release
record; no product code, docs, generated output or CHANGELOG changed.

- `test_prompts_name_the_host_decision_verb_once` partitioned `CHANGELOG.md` at
  `## 0.9.18` and required `## Unreleased` in the head. The v0.9.25 release-notes
  commit `e369be6c` replaced that staging heading with `## 0.9.25`, so the
  assertion failed on clean main even though the #349 entry was present under
  its dated `0.9.19` section (`CHANGELOG.md:126`, `:130`).
- The assertion now locates the immutable #349 entry itself
  (`- **A wrong verb on an unchanged Host-owned checkpoint input settles as
  retained (#349).**`), pins the one dated release section that carries it
  (`## 0.9.19 — 2026-10-18 …`), and asserts `Seats: restart required` inside
  that section. That is strictly stronger than the old head anchor: exactly one
  carrying section, a versioned heading, and the seats line read in its own
  release section.
- Every other assertion in the suite is unchanged.
- Robustness was proven by mutation against the real `CHANGELOG.md` before the
  commit: the new anchor still passes with a new dated section or a new
  `## Unreleased` staging section prepended; it fails on entry removal
  (`AssertionError(carrying=0)`), on the entry moved into `Unreleased`
  (`AssertionError(## Unreleased)`), and on a stripped `Seats:` line
  (`AssertionError(seats)`).

Candidate: `a847c559` on `workflow/issue-402`, which is fix commit `42fa1607`
plus the Host-directed integration of current main `cd6a084f` (which already
carries the #401 merge and sink). Host acceptance: delivery `42fa1607` was
accepted — the Host judged the diff strictly stronger than the old anchor,
noted the mutation robustness proof, and re-ran the suite in the worktree
(39 OK, clean).

## Evidence

- Baseline on `818a8a31`:
  `python3 tests/contract/test-issue-349-checkpoint-verb.py` gave
  `FAILED (failures=1)`, `AssertionError: '## Unreleased' not found`, 39 tests.
- Integrated tree `a847c559`, exit 0: `Ran 39 tests in 21.028s ... OK`.
  Log: `/tmp/kpr-402-integrated-suite.log`.
- `./scripts/render-skills.py --check` on the integrated tree, exit 0:
  `render-skills: PASS (11 workers + kaola-project-runner + kaola-delegator +
  grok-bot host: 1 bridge skill, 2555 B, content stage, unpinned (not
  saveable); budgets OK)`. Log: `/tmp/kpr-402-integrated-render.log`.
- Repo-conventional focused gate on the pre-integration candidate `42fa1607`:
  `./scripts/validate.sh --suite test-issue-349-checkpoint-verb.py` exit 0
  (suite 22.5 s, render check PASS, no residual processes).
- Host acceptance verdict: PASS on `42fa1607`; Host suite re-run: 39 OK, clean.
- Final-validation record bound to the integrated tree (main-resident run
  folder): `kaola-workflow/issue-402/.cache/final-validation.md`, verdict
  `pass`, validated candidate hash
  `5e95d55f741399f64649b828beba52c6d293d79f658c5c338a80aeab2ac43000`.
- Mutation probe: pre-commit, local, on the real file; no repository bytes were
  mutated by the probe.

## Known failures or unverified scope

- This run does not run the whole-inventory gate; per the Host directive it runs
  on merged main afterwards. No whole-inventory green is claimed here.
- Test-only change: no product, transport or platform behavior changed, so no
  live ACP UAT applies.
- The suite assumes the #349 entry and its dated release section stay in
  `CHANGELOG.md` (release history is append-only). It no longer assumes any
  current head heading, so a new release-notes cycle cannot re-break it.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- tests/contract/test-issue-349-checkpoint-verb.py

## Documentation Docking

No documentation or CHANGELOG change: this is test-side alignment only and the
issue scope excludes docs. The #349 entry and its `Seats: restart required`
line already exist in `CHANGELOG.md`; the suite now pins them where they are.
No generated `skills/` or `hosts/` output was authored by this run; the branch
only carries the Host's accepted content-cycle integration from main.

## Follow-Up Items

- Mirror `KaolaBrother/kaola-project-manager#771` is read-only context and is
  left uncommented for the Host.
- No tag, release, install or KPM-side operation is part of this finalization.
- No new issue filed: the run found no further defect beyond the #349
  post-release staleness it fixed.

Final readiness: ready. Merge sink to `main`, verify publication and issue
closure, archive the run under `kaola-workflow/archive/issue-402/`, and remove
the run worktree and branch per the sink.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-402/.cache/final-validation.md
- kaola-workflow/archive/issue-402/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-402/finalization-summary.md
- kaola-workflow/archive/issue-402/mission-ledger.jsonl
- kaola-workflow/archive/issue-402/workflow-state.md
