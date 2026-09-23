# Finalization summary — issue-145 (#145)

## Delivered
Codex `default` tier now applies **GPT-6 Sol High** (`gpt-6-sol`, `effort=high`) on the measured ACP surface
`npx --yes --package @openai/codex@0.155.1 --package @agentclientprotocol/codex-acp@1.13.0 codex-acp`, correcting
the #142 no-effort finding (specific to adapter 1.11.0 / bundled codex 0.153.4, whose catalog omitted gpt-6-sol).
- `platforms/codex.yaml`: `default_model_name "GPT-6 Sol High"`, `default_model_parameters "effort=high"`,
  `default_model_effort "high"`; `acp_command` pins codex 0.155.1 + codex-acp 1.13.0; `acp_verified_versions
  cli=0.155.1;adapter=1.13.0;protocol=1`; `acp_wrapper_pin 1.13.0`; `acp_effort_config_id` stays `reasoning_effort`
  (measured); `steering_summary` names 1.11.0 and 1.13.0 (1.13.0 by source check); `acp_quirks` records the measured
  `CODEX_PATH=/opt/homebrew/bin/codex` (codex-cli 0.156.0) override and that no portable 0.156.1 pin is claimed.
- Owner ruling (2026-09-23 ~12:28 +0800): **option_1_ship_recorded** — keep the npx 0.155.1 + 1.13.0 pins, record the
  CODEX_PATH 0.156.0 override; supersedes the ≥0.156.x target of issuecomment-5788380284. Recorded on the issue in
  issuecomment-5789242692.
- Upgrade tier (`gpt-6-astra`/high) unchanged and re-measured applied on 1.13.0. `host_skill_entry` untouched (#126).

## Files Changed
platforms/codex.yaml; scripts/adapters/codex.sh; generated skills/codex-kaola-project-runner/{SKILL.md,
references/{acp.md,platform.md,steering.md},scripts/{adapters/codex.sh,platform.yaml}}; tests/contract/{mock-acp-agent.py,
test-acp-contract.py,test-issue-22-bypass-all-approvals.py,test-runner-v2.py}; CHANGELOG.md.

## Test Coverage
- test-acp-contract.py: `test_codex_default_applies_model_fast_mode_in_order_without_effort` renamed back to
  `test_codex_default_applies_model_effort_fast_mode_in_order` (reverse of the #142 rename) — default start sends
  model=gpt-6-sol, reasoning_effort=high, fast-mode=off, mode=agent-full-access in order; effort applied; resolved_effort high.
- test-runner-v2.py and test-issue-22-bypass-all-approvals.py: pinned npx command → codex 0.155.1 + codex-acp 1.13.0
  (test-issue-22 is outside validate.sh; run directly: 12 tests OK; test-runner-v2: 4 OK).
- mock-acp-agent.py: gpt-6-sol description cites #142/#145.

## Validation
- chains: `run-chains.js` → `chains_config_missing` (consumer repo, no test:kaola-workflow:*); gate is the agent record.
- `./scripts/render-skills.py --check` — PASS rc=0 (budgets OK) on 9e5199b; re-run rc=0 after the (no-op) rebase check
  against origin/main a421ec2.
- `./scripts/validate.sh` — rc=0 on 9e5199b in 497 s: 283 `ok`, 0 FAIL/ERROR/Traceback, kaola-grok-bot-verify PASS,
  sweep `residual_pids: []` (log validate-145.log). Also rc=0 on 5d42700 (513 s) before the addendum.
- `git diff --check main..HEAD` — rc=0.
- Record: .cache/final-validation.md, command `./scripts/render-skills.py --check && ./scripts/validate.sh`,
  validated_candidate_hash 9ffb97a5b1ed…
- Host acceptance: ACCEPTED on 9e5199b (Host re-ran render --check rc=0 and validate.sh rc=0).
- Live acceptance (measurement legs, no Codex turns, every probe stopped residual_pids []): receipts in
  .cache/probes/ (SUMMARY.md rounds 1–2 + addendum):
  - pinned 1.11.0/0.153.4: no effort option; reasoning_effort=high -32602.
  - 1.13.0/0.155.1: reasoning_effort low..ultra under gpt-6-sol; high applied, effective gpt-6-sol/high; medium
    discriminator applied; upgrade gpt-6-astra/high applied.
  - 1.13.0 + CODEX_PATH 0.156.0: same; child `/opt/homebrew/bin/codex app-server`; high/medium/upgrade applied
    (1 of 3 upgrade starts hit the holder 15 s session/new wait → #146).
  - npx @openai/codex@0.156.1: nested 0.155.1 under the adapter; install stalled twice (bounded) — not probed.
- Not executed: post-merge live `--tier default` receipt from the installed Skill (Host-owned after sink + reinstall);
  live native steering on 1.13.0 (needs a turn; source check only).

## Changed Paths
- CHANGELOG.md
- platforms/codex.yaml
- scripts/adapters/codex.sh
- skills/codex-kaola-project-runner/SKILL.md
- skills/codex-kaola-project-runner/references/acp.md
- skills/codex-kaola-project-runner/references/platform.md
- skills/codex-kaola-project-runner/references/steering.md
- skills/codex-kaola-project-runner/scripts/adapters/codex.sh
- skills/codex-kaola-project-runner/scripts/platform.yaml
- tests/contract/mock-acp-agent.py
- tests/contract/test-acp-contract.py
- tests/contract/test-issue-22-bypass-all-approvals.py
- tests/contract/test-runner-v2.py

## Issue walk
- Scope 1 (measure both surfaces, receipts incl. option ids, applied, effective read-back, config id) → probes SUMMARY
  rounds 1–2; config id `reasoning_effort`.
- Scope 2 (wire default gpt-6-sol+high; yaml fields; render; tests per precedent) → 5d42700; --check PASS.
- Scope 3 (CHANGELOG correction of #142 bullet) → 5d42700 (+9e5199b CODEX_PATH record).
- Scope 4 (HUMAN_DECISION_REQUIRED only if high unmeasurable) → not triggered for high; a separate
  HUMAN_DECISION_REQUIRED on the ≥0.156.x pin wiring was ruled option 1 by the Owner.
- Owner correction comment (≥0.156.x) → superseded by the Owner ruling; recorded on the issue before close.
- Out of scope respected: #126, release cut, no Fable.

## Documentation Docking
.cache/doc-docking.md — DOCKED.

## Follow-Up Items
- filed: #146 (P2, bug) — holder's fixed 15 s session/new wait shorter than live codex latency; confirmed exists,
  OPEN, body 2177 chars.

## Status
READY — accepted; finalize + merge sink.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-145/.cache/doc-docking.md
- kaola-workflow/archive/issue-145/.cache/final-validation.md
- kaola-workflow/archive/issue-145/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-145/.cache/probes/113-medium-start.json
- kaola-workflow/archive/issue-145/.cache/probes/113-medium-stop.json
- kaola-workflow/archive/issue-145/.cache/probes/113-start.json
- kaola-workflow/archive/issue-145/.cache/probes/113-stop-1.json
- kaola-workflow/archive/issue-145/.cache/probes/113-stop.json
- kaola-workflow/archive/issue-145/.cache/probes/113-upgrade-start.json
- kaola-workflow/archive/issue-145/.cache/probes/113-upgrade-stop.json
- kaola-workflow/archive/issue-145/.cache/probes/SUMMARY.md
- kaola-workflow/archive/issue-145/.cache/probes/ab-ab155-1-start.json
- kaola-workflow/archive/issue-145/.cache/probes/ab-ab155-1-stop.json
- kaola-workflow/archive/issue-145/.cache/probes/ab-ab155-2-start.json
- kaola-workflow/archive/issue-145/.cache/probes/ab-ab155-2-stop.json
- kaola-workflow/archive/issue-145/.cache/probes/ab-ab155-3-start.json
- kaola-workflow/archive/issue-145/.cache/probes/ab-ab155-3-stop.json
- kaola-workflow/archive/issue-145/.cache/probes/ab-ab156-1-start.json
- kaola-workflow/archive/issue-145/.cache/probes/ab-ab156-1-stop.json
- kaola-workflow/archive/issue-145/.cache/probes/ab-ab156-2-start.json
- kaola-workflow/archive/issue-145/.cache/probes/ab-ab156-2-stop.json
- kaola-workflow/archive/issue-145/.cache/probes/ab-ab156-3-start.json
- kaola-workflow/archive/issue-145/.cache/probes/ab-ab156-3-stop.json
- kaola-workflow/archive/issue-145/.cache/probes/cp156-process-tree.txt
- kaola-workflow/archive/issue-145/.cache/probes/cp156-start.json
- kaola-workflow/archive/issue-145/.cache/probes/cp156-stop.json
- kaola-workflow/archive/issue-145/.cache/probes/cp156m-start.json
- kaola-workflow/archive/issue-145/.cache/probes/cp156m-stop.json
- kaola-workflow/archive/issue-145/.cache/probes/cp156u-start.json
- kaola-workflow/archive/issue-145/.cache/probes/cp156u-stop.json
- kaola-workflow/archive/issue-145/.cache/probes/cp156u2-start.json
- kaola-workflow/archive/issue-145/.cache/probes/cp156u2-stop.json
- kaola-workflow/archive/issue-145/.cache/probes/cp156u3-start.json
- kaola-workflow/archive/issue-145/.cache/probes/cp156u3-stop.json
- kaola-workflow/archive/issue-145/.cache/probes/pinned-start.json
- kaola-workflow/archive/issue-145/.cache/probes/pinned-stop.json
- kaola-workflow/archive/issue-145/.cache/probes/record-options-113.json
- kaola-workflow/archive/issue-145/.cache/probes/record-options-113m.json
- kaola-workflow/archive/issue-145/.cache/probes/record-options-113u.json
- kaola-workflow/archive/issue-145/.cache/probes/record-options-cp156.json
- kaola-workflow/archive/issue-145/.cache/probes/record-options-cp156m.json
- kaola-workflow/archive/issue-145/.cache/probes/record-options-cp156u.json
- kaola-workflow/archive/issue-145/.cache/probes/record-options-cp156u2.json
- kaola-workflow/archive/issue-145/.cache/probes/record-options-cp156u3.json
- kaola-workflow/archive/issue-145/.cache/probes/record-options-pinned.json
- kaola-workflow/archive/issue-145/finalization-summary.md
- kaola-workflow/archive/issue-145/mission-ledger.jsonl
- kaola-workflow/archive/issue-145/workflow-state.md
