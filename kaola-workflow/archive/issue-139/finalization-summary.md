# Finalization Summary — issue-139

## Delivered
#139 was closed as an OVERTURNED MEASUREMENT. The claim "cursor-cli default tier does not land" was measured on a probe surface where initialize did not deliver `clientCapabilities._meta.parameterizedModelPicker`. The real Runner path sends that flag (scripts/kaola-acp-holder.py:1520). With it, cli 2026.09.18-9a7762b advertises bare ids plus separate effort options (4 of 4 sessions). `start --tier default` landed grok-4.7 with reasoning_effort=xhigh and fast=false. `--tier upgrade` landed claude-fable-5-1 with effort=high; fast was rejected and honestly reported as unknown. The composite-only schema, the -32602 bare-id rejection, and the cli-config xhigh→high degradation all occur only when the flag is absent. Owner ruling 2026-09-22: no code or config change and no composite fallback. Closing comment: https://github.com/KaolaBrother/kaola-project-runner/issues/139#issuecomment-5779074576

## Files Changed
None (no implementation commit). Run records only.

## Test Coverage
None added; there was no behavior change to cover.

## Validation
`./scripts/render-skills.py --check` → PASS on the unchanged tree at ca7e7f3 (recorded in .cache/final-validation.md). `./scripts/validate.sh` was not run: no candidate existed (Owner ruling), and mission 3 is recorded as failed/not-applicable in the ledger.
Acceptance legs: live native probes and real-path Runner starts, with evidence in evidence/ (a copy is kept at /tmp/kpr-139-evidence/). cli-config.json and acp-config.json were restored byte-identical after the probes.

## Changed Paths
[] (finalize check reported changed_paths: [])

## Documentation Docking
DOCKED — no impact (.cache/doc-docking.md).

## Follow-Up Items
None filed, per Owner. Two side findings are recorded as facts on #139: (1) one session/new answered after ~16 s, past the holder's 15 s window (acp-session-timeout plus orphan_response); an immediate retry succeeded. (2) Successful real-path starts write ~/.cursor/cli-config.json with correct values.

## Status
READY — close #139, archive, no-op sink.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-139/.cache/doc-docking.md
- kaola-workflow/archive/issue-139/.cache/final-validation.md
- kaola-workflow/archive/issue-139/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-139/evidence/nometa-set.json
- kaola-workflow/archive/issue-139/evidence/p1-new.json
- kaola-workflow/archive/issue-139/evidence/p2-nometa.json
- kaola-workflow/archive/issue-139/evidence/p3-apply.json
- kaola-workflow/archive/issue-139/evidence/probe.py
- kaola-workflow/archive/issue-139/evidence/rep1.json
- kaola-workflow/archive/issue-139/evidence/rep2.json
- kaola-workflow/archive/issue-139/evidence/rep3.json
- kaola-workflow/archive/issue-139/evidence/start-default.json
- kaola-workflow/archive/issue-139/evidence/start-default2.json
- kaola-workflow/archive/issue-139/evidence/start-upgrade.json
- kaola-workflow/archive/issue-139/finalization-summary.md
- kaola-workflow/archive/issue-139/mission-ledger.jsonl
- kaola-workflow/archive/issue-139/workflow-state.md
