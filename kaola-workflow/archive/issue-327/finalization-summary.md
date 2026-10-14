# Finalization Summary — issue-327

## Delivered

Grok worker `grok-KPR-i327-retire-path` (grok/default) implemented the state-tool retire path for
obsolete pre-v0.9.12 `maintenance-returned` inputs in commit `f6591c05` on `workflow/issue-327`
(base = main `f42805a6`):

1. **Input classification** (`obsolete_input_class`): the three pre-v0.9.12 shapes —
   `batch:<rev>` unbound failure ids (the 1261/1444/1669 ranges), `host:tasks/<id>@<rev>` returned
   business changes, and bare not-in-batch task ids (`why` `not-in-batch`). Stop duties never match
   this shape; named batches (`batch:b-…`) stay on the checkpoint path.
2. **Original-evidence references** (`obsolete_evidence_kind`): exactly the four owner-named kinds
   — retired task row, closed issue, stopped node holder, superseded revision. Each input is
   removed only with the same update and one reference that checks out; **unproven inputs still
   refuse** (`input-unproven` preserved).
3. **Alert clearing**: the `maintenance-returned` alert leaves the file only when no input
   remains; the refusal route text names the per-input removal path.
4. **No new wake, no re-queue, no node traffic**; all-idle wake ordering and normal queue handling
   untouched (grep-verified empty diff in wake/followups logic).
5. New suite `test-issue-327-obsolete-returned-inputs.py` (4 tests: retire-with-evidence,
   unproven-still-refuse, alert-clears-only-empty, checkpoint settlement still raises
   host_revision) registered in both validate.sh lists; renders regenerated; CHANGELOG Unreleased
   with `Seats: restart not required` (state-tool/CLI change only — recorded per its line).

## Candidate

Branch `workflow/issue-327`, single commit `f6591c05` over main `f42805a6`.
Recorder-bound hash: `c9bcaca4d9292c47…`.

## Evidence

- Worker fp `387e3461…`; two turns (implement + record-verify wrap-up); worker's own runs: new
  suite green, adjacent suites green, render PASS; full inventory honestly not run by the worker.
- Host runs on the exact candidate: full inventory `./scripts/validate.sh` **rc=0** (1513 s,
  proxies and ambient `KAOLA_ACP_DISPATCHER` unset — including the timing-sensitive 255 suite);
  `render-skills.py --check` PASS; suite 327 green standalone.
- One `test-issue-255` wait_for test failed standalone under load but fails identically on
  unmodified main in the same conditions (pre-existing flake; passed in the full run).
- Validation record: `kaola-workflow/issue-327/.cache/final-validation.md` (verdict pass).

## Known failures and unverified scope

- Worker-declared out of scope (not implemented): a terminal path for `recovery#` inputs whose
  original record is already gone. Recorded here; no new issue filed (no new KPR issues without
  owner direction).
- No live `.kaola` state file was modified by this run (worker verified; the real heartbeat was
  untouched). Live retirement of the KPM Host's 28 inputs happens by its own operator after this
  fix ships and restarts.

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
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- tests/contract/test-issue-327-obsolete-returned-inputs.py

## Follow-Up Items

- The `recovery#`-gone-original terminal path remains open as a potential follow-up for the owner
  to direct; not filed per the no-new-issues rule.
- searched: duplicate probe `gh issue list --state all --search "input-unproven retire"` before
  the run → only #327 itself.

## Final readiness

Ready: candidate accepted (Host review + full inventory green on the candidate), validation
recorded pass, no tag/release/install performed.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-327/.cache/final-validation.md
- kaola-workflow/archive/issue-327/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-327/finalization-summary.md
- kaola-workflow/archive/issue-327/mission-ledger.jsonl
- kaola-workflow/archive/issue-327/workflow-state.md
