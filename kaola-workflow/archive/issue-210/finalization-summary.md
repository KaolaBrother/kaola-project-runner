# Finalization Summary — issue-210

## Delivered

Issue #210 ("Keep Host cwd protection in the mandatory Skill entry"), authorized minimal change,
part by part → evidence (commit 80904067):

- Promote the essential Host cwd rule into the always-loaded orchestrator Skill, near the Host
  operating boundary → `templates/orchestrator/SKILL.md.tmpl` `### Hosts` section, new sentence:
  "Keep the Host shell cwd at the canonical root: never `cd` into a worktree finalize/sink may
  remove; use absolute paths, `git -C`, or `(cd ... && ...)`."
- Reconcile `references/workflow-worktree.md` so "enter then return before finalize" is not the
  primary safe procedure → `## Host shell cwd` section rewritten: entering-and-returning is now
  stated as *not safe*; absolute paths / `git -C` / subshell stated as the primary procedure,
  cwd staying at root throughout. The #137 bricked-Host recovery line and the subshell option are
  preserved verbatim.
- Do not raise byte budgets; compact rule, offset by trims if needed; record before/after sizes →
  see Files Changed below. Trims were verified against the contract-test suite before applying
  (one candidate trim was reverted after it broke a pinned #52 marker; the final set is
  test-clean).
- Never repeat the warning in heartbeat bodies, no new recovery procedure, no runtime
  patch/registry/watchdog/shell interception/automatic replay → none added; only the one rule
  sentence plus the reference reconciliation.
- Update stale test expectations only where they pinned the old wording → one marker updated in
  `tests/contract/test-generated-skills.py` (the consumer-boundary sentence whose exact wording
  changed as an offsetting trim); all other candidate trims were pre-verified as unpinned.
- Coordinate with #208 (future consolidation) — kept the rule a single short authoritative
  statement, no broader restructuring attempted.

Host acceptance: ZCode Host zcode-KPR-orchestrator-main (holder 626a061e) accepted tip 80904067
and authorized finalize (merge sink, push, close, archive; no release/tag/install).

## Files Changed

`templates/orchestrator/SKILL.md.tmpl`, `templates/orchestrator/references/workflow-worktree.md`,
`tests/contract/test-generated-skills.py`; regenerated `skills/kaola-project-runner/{SKILL.md,
references/workflow-worktree.md}` + 9 other platforms' `scripts/main-skill-build.json` (hash
bookkeeping side effect of re-rendering the shared orchestrator content). Commit 80904067.

Rendered bytes (budget unchanged) before 2b0529ec → after 80904067:
- kaola-project-runner/SKILL.md: 17401 → 17399 / 17408 (budget headroom 7 B → 9 B)
- kaola-project-runner/references/workflow-worktree.md: 4734 → 4858 / 8192

## Test Coverage

`./scripts/render-skills.py --check` PASS (budgets OK) on 80904067. Ran the actual contract test
files directly (not just render --check): `test-issue-52-workflow-worktree.py`,
`test-issue-41-orchestrator.py`, `test-issue-49-grok-bot-host.py`, `test-generated-skills.py` —
all pass. Full `./scripts/validate.sh` on 80904067: exit 1 with exactly
`test-issue-65-host-contract` (2: `test_reference_keeps_turn_end_and_exit_as_equal_triggers`,
`test_reference_starts_the_worker_from_the_host_with_a_runnable_example`) and
`test-issue-162-upgrade-safety` (1: `test_release_note_rule_and_no_rebind_wording`) failing;
verified byte-for-byte identical assertion output on a clean run of the same two test files
against main (2b0529ec) — pre-existing, tracked as #209, unrelated to this change (neither touches
`zcode-host-dispatch.md`, and the "no rebind" phrase was already absent from `SKILL.md.tmpl`
before this change per `git show HEAD`). All other suites PASS.

## Validation

classification: final_validation_stale
green: false
mode: final-validation

recorded validated_candidate_hash "459043c6a4acf0357bda8589a7e4041a634f777bb53c9631bb66c2e5fd2eb63a" != current code-tree hash "075b775512f730d2c66515b492ca4d656c9bbddd666c2648f60e4602fdb5a827" — a relevant source/test/test-consumed file changed after the recorded validation; re-run the validation command and re-record final-validation.md with a fresh hash

A relevant source/test/test-consumed file changed after validation — or the record was written from a different checkout than this one. Re-run the validation command, then re-record with `kaola-workflow-validation-runner.js record --project <project> --verdict pass --command "<the validation command you ran>"`, invoked from the working tree you validated (the gate hashes the tree its own shell is in, and a linked worktree and main differ until the branch merges); never hand-patch the hash.

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/workflow-worktree.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/workflow-worktree.md
- tests/contract/test-generated-skills.py

## Documentation Docking

DOCKED — see `.cache/doc-docking.md`. No-impact across README.md, docs/architecture.md,
docs/conventions.md, docs/api.md (grepped for old/new wording: no surface quotes this Skill's
prose). No CHANGELOG entry added: internal Skill-prompt correction, no operator-test path
(`scripts/kaola-acp-holder.py`, `kaola-zcode-acp.py`, `kaola-quota.py`, `scripts/adapters`,
`platforms`) touched, matching precedent (`fix(runner): #198 ...` landed without one).

## Follow-Up Items

- Filed `#212` — "Finalize residue-mirror step has no ownership guard for foreign untracked
  files (recurred: #192, #194, #206)", labeled P2. Confirmed exists, state OPEN, non-empty body
  (2929 chars). Discovered while applying this finalize's protected-docs guard (see Sink notes in
  `workflow-state.md`): the same untracked-file-mirroring bug that hit #192/#194 recurred a third
  time for #206 (dangling commit `cf7d5db8`, never pushed), with only a manual per-finalize
  `.git/info/exclude` workaround each time and no permanent code fix. Out of scope for #210 itself.

## Readiness

Ready to sink. All acceptance-criteria parts have evidence above; no blockers; no open questions
requiring the user.

## Finalize Findings

### residue_unattributed

The `chore: finalize` commit did NOT carry the paths below: this branch's own commits touch no file in their directories, so the transaction has no evidence they are this run's work. Nothing was committed, reverted or deleted — they are exactly where they were. Read them before the sink runs: commit what belongs to the run, remove what does not.

Paths not attributed to this run:

- .cache/doc-docking.md
- .cache/final-validation.md

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-210/.cache/doc-docking.md
- kaola-workflow/archive/issue-210/.cache/final-validation.md
- kaola-workflow/archive/issue-210/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-210/finalization-summary.md
- kaola-workflow/archive/issue-210/mission-ledger.jsonl
- kaola-workflow/archive/issue-210/workflow-state.md
