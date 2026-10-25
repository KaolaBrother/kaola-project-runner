# Finalization Summary: issue-412

## Delivered
- Host-view node liveness: a state file with no carrier, or with a carrier from an earlier holder of the same Host session, now proves the dispatcher from that Host's own live record. The view also reports `sideagent_node_holder` (Expected 1, partly).
- A range already inside `maintenance-returned` now gets an executable Host route: `state recovery-input --kind request`. The state tool is found the same way the holder finds it. If no tool is found, the view names the missing prerequisite. A returned stop duty is named first. The holder is unchanged and nothing replays automatically (Expected 2, partly).
- The dead-holder unknown route retires a per-item `cancelled` disposition and reports it as `cancelled` (Expected 3; real stub: kw1116).
- Corrections to the issue premise: the dead-checkpoint pin as the cause and the blanket claim "no automatic path" were contradicted. The split-roots change was tried and dropped.

## Candidate
- Branch `workflow/issue-412`, rebased onto main 48209f4b: commits cdab0c05 and ec859606. The Host accepted these as 01eebe58 (round-3 PASS). The tree diff against 01eebe58 is only main's 255 fixture change.

## Acceptance
- Host acceptance came after a three-round independent review (precheck CONTRADICTION, round-2 bounded finding, repair, round-3 PASS). Evidence: `/tmp/kpr-i412-precheck.md` and `/tmp/kpr-i412-fix/report.md`.

## Evidence
- `/tmp/kpr-i412-fix/final-suites.log`: suites 412 (31 OK) and 255 (171 OK) on the rebased tree.
- `/tmp/kpr-i412-fix/final-render.log`: `render-skills.py --check` passes.
- `/tmp/kpr-i412-fix/red-baseline.log` and `red-ec6ebfd6.log`: red evidence on 7adc08c2 and on ec6ebfd6.

## Known failures or unverified scope
- The original vrpai cause is not verified; no vrpai receipts were available.
- Split record roots and adoption of a node dispatched by an earlier Host incarnation were not addressed.
- Retire-stub classes 2-4 were not addressed: the i369 family (collected proof, session absent from --live) and profiles-20261026 (dispatch refs that are not index items).
- This was a subset suite run, not full-inventory coverage.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- docs/dispatch-collect.md
- scripts/kaola-dispatch.py
- scripts/kaola-record-contract.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-record-contract.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/kaola-record-contract.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-record-contract.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-record-contract.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-record-contract.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-record-contract.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-record-contract.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kaola-project-runner/scripts/kaola-record-contract.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- tests/contract/test-issue-412-maintenance-owed-retire.py

## Follow-Up Items
- None filed in this run. The residual classes are listed above for the Host to decide.

## Readiness
- Ready to sink (merge to main, close #412). No release, tag or install: the owner hold is in place.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-412/.cache/final-validation.md
- kaola-workflow/archive/issue-412/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-412/finalization-summary.md
- kaola-workflow/archive/issue-412/mission-ledger.jsonl
- kaola-workflow/archive/issue-412/workflow-state.md
