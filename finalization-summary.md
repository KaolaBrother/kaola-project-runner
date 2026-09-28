# Finalization Summary — Issue #212

## Delivered

The KPR portion of the paired design with Kaola-Workflow #1110: Host-side
finalize safeguards for foreign files, as one new section
`## Foreign files and finalize safeguards` in the Project Runner
`workflow-worktree` reference (source template and generated copy), stated
exactly once — no main-SKILL, doc-maintenance, issue-dispatch, or heartbeat
edits, so the merged #208 wording stands untouched.

The four duties, faithful to the issue body:

1. When a known foreign/protected file or an upstream finalize limitation
   affects the current run, the Host conveys that concrete constraint to the
   worker responsible for finalization through existing task/run records; the
   Skill adds no global ownership table, scan schedule, classifier, or filter.
2. The finalizing worker reads the run's existing Workflow
   preview/finalization receipts, preserves unrelated files, and reports
   ownership ambiguity or a blocked sink honestly; copying a file mechanically
   does not establish that it belongs to the task; never delete, stage, or
   adopt unrelated files merely to clean the checkout.
3. The Host reuses those receipts plus the candidate diff for
   acceptance/closeout — confirming known protected paths did not enter the
   delivered candidate/archive and that any temporary protection was restored;
   concrete mismatches return to the responsible worker; no second acceptance
   engine, no unconditional duplicate test run.
4. The affected run keeps its narrow `.git/info/exclude` protection
   (byte-preserved baseline, scoped protection applied before mirroring/sink,
   restoration on completion or interruption, coordinated shared edits,
   exact-remaining-duty reporting when restoration is unsafe) as a temporary,
   project-specific measure; the section names no file.

Retirement is by conditions, not issue closure: remove the workaround only
after an authorized fixed-version adoption plus the bounded consumer evidence
that the known foreign file stays excluded and unchanged; the general handoff
and receipt duties are durable.

Honest upstream status: **Kaola-Workflow #1110 remains UNRESOLVED.** This run
delivers consumer-side guidance and the retained scoped mitigation only; no KW
fix is claimed, merged, or deployed, and no KPR code, installed plugin, or
external repository was touched.

## Files Changed

- `templates/orchestrator/references/workflow-worktree.md` (source; 4827 →
  7501 B against the unchanged 8192 B ceiling)
- `skills/kaola-project-runner/references/workflow-worktree.md` (rendered,
  byte-identical to source)
- `skills/<10 platforms>-kaola-project-runner/scripts/main-skill-build.json`
  (regenerated hash manifests via `render-skills.py --write`)
- `CHANGELOG.md` (Unreleased entry, guidance only, `Seats: restart not
  required`)
- Run state: `finalization-summary.md`, `.cache/doc-docking.md`

## Test Coverage

Focused, diff-scoped chains on the frozen candidate `cb75fc0e` (and re-run at
finalize): `./scripts/render-skills.py --check` PASS with budgets OK;
`tests/contract/test-issue-52-workflow-worktree.py` 9/9 OK (the suite pinning
the edited reference); `tests/contract/test-progressive-disclosure.py` 15/15
OK (byte budgets). Contract suites 65 and 162 were not run: they pin nothing
in this reference and their three known failures on main belong to in-flight
#209, untouched by this run.

## Validation

## Changed Paths

## Documentation Docking

DOCKED — `.cache/doc-docking.md`. CHANGELOG updated; the `docs/architecture.md`
pointer to the generated reference remains accurate (additive section); all
other checked surfaces no-impact with reasons recorded there.

## Follow-Up Items

- Kaola-Workflow #1110 (open, upstream-owned): the mechanical finalize
  mirror/staging fix. After an authorized fixed-version adoption plus the
  bounded consumer evidence, remove the run-scoped exclude workaround per the
  section's retire-by-conditions paragraph — never merely because an issue
  closed. No new KPR follow-up filed: the run discovered nothing beyond the
  already-filed upstream defect.
- Current mitigation state at this finalize: main-checkout
  `.git/info/exclude` baseline 541 B (sha256
  `321dffcb77a68a6c079d35da12944866b895b4cc9fb3b1fae72fe9468c7eafeb`),
  restored byte-exact after sink; both protected research docs untouched and
  unstaged throughout.

Final readiness: ready. Merge sink to `main`, close #212 with the
upstream-UNRESOLVED statement, archive, then remove the run worktree and
branch. No release, tag, or install.
