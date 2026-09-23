# Finalization summary — issue-126

## Delivered
Issue #126: codex is admitted as a Project Runner Host with its live-measured entry `$kaola-project-runner` (Scope 1 carried from #122).
- `host_skill_entry: "$kaola-project-runner"` in platforms/codex.yaml and the HOST_SKILL_ENTRIES twin in scripts/kaola-acp.py, filled only after the M0 probe was green (commit 2394d57).
- host-entry-matrix codex row from the evidence: E2; E2 / E2, codex-acp 1.13.0.
- The #122 fail-closed rule is unchanged. Its tests now run on an installed-tree fixture with codex's entry emptied.
- Host acceptance: ACCEPTED adcb2e9 (Host verdict 2026-09-23, after the gate rc=0).

Issue statement walk:
- "fresh ACP session, new-build-only anchor, negative control": evidence/m0-trigger/C-codex.json (E2, anchor added afeb43b 2026-09-22) and N-codex.json (SKILL-NOT-LOADED).
- "D3 steps 2 and 5 under shadow HOME + isolated KAOLA_ACP_RECORD_ROOT": evidence/d3/analysis.json (step2 E2 [6,250], step5 E2 [251,457]) and uat.json (bound, carrier fingerprint match, exact stops).
- "sweep 0": evidence/d3/sweep-final.json (matched [] residual [] rc 0), ps-after-sweep.txt (0 kpr126 processes).
- "fill manifest + HOST_SKILL_ENTRIES + matrix row only with that evidence": commits 2394d57 and 7533c28; test_manifest_entries_are_the_code_table.
- "until then codex stays refused": the entry commit follows the green M0; D3 ran on the entry build because an entry-less Host start refuses.

## Files Changed
Commits on workflow/issue-126:
- 2394d57 (entry + render).
- 7533c28 (tests, matrix, docs, CHANGELOG).
- adcb2e9 (review F1–F3: heartbeat skeleton Host carrier wording + pin; matrix roots/quoting note; CHANGELOG).

## Test Coverage
- tests/contract/test-issue-119-host-entry.py 11/11, 160 checks:
  - codex entry pinned.
  - test_issue_122_entryless_host_fails_closed T1/T3 on the emptied-entry fixture.
  - T2: ten capable platforms.
  - T4: the shipped codex Host admits and binds.
  - T5: matrix row.
  - New test_issue_126_codex_host_carrier: carrier line 1 `$kaola-project-runner`, line 2 `(Codex CLI Host)`.
- tests/contract/test-zcode-heartbeat-contract.py 23/23, 476 checks:
  - Entry-less target, holder worker_event rejection and P5 run on the fixture.
  - The skeleton pin is updated.
- Live evidence (not in validate.sh): kaola-workflow/archive/issue-126/evidence/ (README.md indexes every step with the build it ran on).
- Review mutation checks showed the fixture rows are not vacuous (evidence/review-7533c28.md).

## Validation
- `./scripts/render-skills.py --check && ./scripts/validate.sh`, detached, on adcb2e93e0350030c0483782417dfe17274dba97: rc=0 at 2026-09-23T17:20:01.
  - Logs: evidence/validate-adcb2e9.{log,exit,head}.
  - The log shows 49 tests OK, a clean residual sweep, and zero FAIL lines.
- Recorded in .cache/final-validation.md: verdict pass, validated_candidate_hash e8808b32116f….
- run-chains: chains_config_missing (consumer repo; the recorded final validation is the gate).
- Superseded: the gate on 7533c28 was killed when the review fixes mutated the tree. evidence/validate-7533c28-superseded-killed.log is not evidence.
- Acceptance legs:
  - Automated: validate.sh.
  - Live UAT: M0 + D3 + sweep, 2026-09-23 on this Mac.
  - Independent review: no blocker or major finding.
  - Host acceptance: ACCEPTED.

## Changed Paths
finalize --check reported changed_paths (source-scoped):
- platforms/codex.yaml
- scripts/kaola-acp.py
- skills/*-kaola-project-runner/scripts/kaola-acp.py (10 workers)
- skills/*-kaola-project-runner/scripts/main-skill-build.json (10 workers)
- skills/codex-kaola-project-runner/scripts/platform.yaml
- skills/kaola-project-runner/references/heartbeat-skeleton.md
- skills/kaola-project-runner/references/host-entry-matrix.md
- templates/orchestrator/references/heartbeat-skeleton.txt
- templates/orchestrator/references/host-entry-matrix.md
- tests/contract/test-issue-119-host-entry.py
- tests/contract/test-zcode-heartbeat-contract.py

Also changed: CHANGELOG.md, docs/api.md, docs/codex-host.md, docs/zcode-host.md.

## Documentation Docking
DOCKED — see .cache/doc-docking.md.

## Follow-Up Items
- filed: #149 (P3, enhancement): whether the Codex user-level SessionStart(compact) hook fires in an ACP codex Host, and aligning it with Host recovery (review S1, unmeasured). Confirmed OPEN, body 1486 chars.
- filed: #150 (P3, documentation): the main Skill still says "nine" platform Runner Skills (ten since #98). Pre-existing. Confirmed OPEN, body 1032 chars.
- Observations, not defects:
  - Under a shadow HOME, dsh has no provider credential and claude-code is not logged in, so the D3 worker was codex.
  - Three parallel cold npx codex starts all hit acp-initialize-timeout; sequential starts were ready in about 9 s.

## Readiness
READY. Host accepted, validation pass recorded, docs docked, follow-ups filed. Close #126 through the merge sink.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-126/.cache/doc-docking.md
- kaola-workflow/archive/issue-126/.cache/final-validation.md
- kaola-workflow/archive/issue-126/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-126/evidence/README.md
- kaola-workflow/archive/issue-126/evidence/d3/1-host-start.json
- kaola-workflow/archive/issue-126/evidence/d3/2-handoff-send.json
- kaola-workflow/archive/issue-126/evidence/d3/5-worker-status.json
- kaola-workflow/archive/issue-126/evidence/d3/6-host-stop.json
- kaola-workflow/archive/issue-126/evidence/d3/analysis.json
- kaola-workflow/archive/issue-126/evidence/d3/analyze.py
- kaola-workflow/archive/issue-126/evidence/d3/carrier-rebuilt.txt
- kaola-workflow/archive/issue-126/evidence/d3/d3.py
- kaola-workflow/archive/issue-126/evidence/d3/driver.exit
- kaola-workflow/archive/issue-126/evidence/d3/host-events.jsonl
- kaola-workflow/archive/issue-126/evidence/d3/ps-after-sweep.txt
- kaola-workflow/archive/issue-126/evidence/d3/summary.json
- kaola-workflow/archive/issue-126/evidence/d3/sweep-final.exit
- kaola-workflow/archive/issue-126/evidence/d3/sweep-final.json
- kaola-workflow/archive/issue-126/evidence/d3/sweep-positive-control.json
- kaola-workflow/archive/issue-126/evidence/d3/uat.json
- kaola-workflow/archive/issue-126/evidence/d3/uat.py
- kaola-workflow/archive/issue-126/evidence/m0-trigger/A-codex.json
- kaola-workflow/archive/issue-126/evidence/m0-trigger/C-codex.json
- kaola-workflow/archive/issue-126/evidence/m0-trigger/N-codex.json
- kaola-workflow/archive/issue-126/evidence/m0-trigger/attempt1-parallel-init-timeout/A-codex.json
- kaola-workflow/archive/issue-126/evidence/m0-trigger/attempt1-parallel-init-timeout/C-codex.json
- kaola-workflow/archive/issue-126/evidence/m0-trigger/attempt1-parallel-init-timeout/N-codex.json
- kaola-workflow/archive/issue-126/evidence/m0-trigger/attempt1-parallel-init-timeout/run-m0.exit
- kaola-workflow/archive/issue-126/evidence/m0-trigger/kpr126-run.sh
- kaola-workflow/archive/issue-126/evidence/m0-trigger/probe.py
- kaola-workflow/archive/issue-126/evidence/m0-trigger/run-m0.exit
- kaola-workflow/archive/issue-126/evidence/m0-trigger/run-m0.sh
- kaola-workflow/archive/issue-126/evidence/review-7533c28.md
- kaola-workflow/archive/issue-126/evidence/validate-adcb2e9.exit
- kaola-workflow/archive/issue-126/evidence/validate-adcb2e9.head
- kaola-workflow/archive/issue-126/finalization-summary.md
- kaola-workflow/archive/issue-126/mission-ledger.jsonl
- kaola-workflow/archive/issue-126/workflow-state.md
