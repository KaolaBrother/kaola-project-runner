# Finalization summary — issue-135

## Delivered
Issue #135: the cursor-cli default tier lands Grok 4.7 **Extra High** again on Cursor CLI 2026.09.18-9a7762b. Cursor's effort option id is a property of the selected model's schema (grok-4.7 `reasoning_effort`, claude-fable-5-1/grok-4.6 `effort`), so `acp_effort_config_id` is now the ordered candidate list `reasoning_effort;effort`, resolved against the options the agent advertises after the model apply (first candidate literally when none is advertised). Receipts add `config_application.effort.candidates`/`advertised` and `effective_selection.effort_config_id`.
- Design (Host-accepted): `evidence/cursor-effort-config-id-design.md` (direction 1′); Owner correction issuecomment-5773251004: no PR, Workflow sink-merge.
- Candidate: workflow/issue-135 @ b279678 (847ca90 impl, 08eea7c test pins + model-neutral quirk, b279678 docs/api.md receipt field), base main d2d2953.
- Host acceptance: PASS (2026-09-22), on receipts smoke-default.json / smoke-upgrade.json and validate exit 0.

## Files Changed
platforms/cursor-cli.yaml; scripts/kaola-acp.py (parse_config_id_candidates, resolve_config_id, apply loop, effective_selection); templates/references/acp.md.tmpl; docs/api.md; CHANGELOG.md; tests/contract/{mock-acp-agent.py,test-acp-contract.py,test-issue-119-host-entry.py,test-issue-130-pty-retired.py}; rendered skills/*/references/acp.md, skills/*/scripts/kaola-acp.py, skills/cursor-cli-kaola-project-runner/scripts/platform.yaml.

## Test Coverage
test-acp-contract.py: default tier sends reasoning_effort=xhigh with advertised/candidates/effective_selection pinned; upgrade tier sends effort=high (regression guard against a naive flip); fast-variant decomposition; new test_cursor_effort_candidates_fall_back_literally (gpt-5.6-sol advertises neither → literal reasoning_effort, applied false, live -32602 text, session still usable); new test_cursor_manifest_declares_effort_candidates; new test_single_effort_id_resolves_to_itself (grok). Mock Cursor agent now advertises a per-model option set mirroring probe-9. test-issue-119/130 exact effective_selection pins extended with effort_config_id.

## Validation
- final-validation: `.cache/final-validation.md` verdict pass (validated_candidate_hash 3baafe20…7e26d), candidate b279678.
- b279678: render-skills.py --check PASS; validate.sh exit 0 (`evidence/validate-b279678.log`); git diff --check d2d2953..b279678 clean.
- 08eea7c: validate.sh exit 0 (`evidence/validate-08eea7c.log`). 847ca90: validate exit 1 (`evidence/validate-847ca90.log`, four exact effective_selection pins + quirk token leakage) — superseded, not a pass.
- run-chains: chains_config_missing — consumer repo; finalize gates on the recorded final-validation (#475).
- Live acceptance (design §9, cursor-agent 2026.09.18-9a7762b, candidate 08eea7c copy-installed to ~/.agents/skills; b279678 changes only docs/api.md, which is not installed): smoke-default.json sha256 bfc8c4e6beed8722948a8a4ee9dbcf91ec858073696938917cc97452adfe013b — reasoning_effort=xhigh "Extra High", effective xhigh, fast false/off; smoke-upgrade.json sha256 d1ac110105f1a7d0d1bb9c5383b38177773ce87892a8d5853f2fc9a5de437876 — effort=high "High", effective high; both stops stopped:true, residual []. Summary `evidence/implementation-and-smoke.md`.

## Issue walk (#135)
- Default-tier receipt shows effective effort xhigh / value_name "Extra High" with fast=false → smoke-default.json.
- Upgrade tier unaffected → smoke-upgrade.json (effort via `effort`=high) + test_cursor_upgrade_tier_maps_fable_base_id.
- render --check and validate.sh pass → Validation above.
- Delivery: body said "PR, no sink-merge"; superseded by the Owner comment issuecomment-5773251004 → Workflow sink-merge.
- Stale manifest evidence (acp_quirks, acp_verified_versions) refreshed → platforms/cursor-cli.yaml.

## Changed Paths
- CHANGELOG.md
- docs/api.md
- platforms/cursor-cli.yaml
- scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/references/acp.md
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/references/acp.md
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/references/acp.md
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/platform.yaml
- skills/devin-kaola-project-runner/references/acp.md
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/references/acp.md
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/references/acp.md
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/references/acp.md
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/references/acp.md
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/references/acp.md
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/references/acp.md
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- templates/references/acp.md.tmpl
- tests/contract/mock-acp-agent.py
- tests/contract/test-acp-contract.py
- tests/contract/test-issue-119-host-entry.py
- tests/contract/test-issue-130-pty-retired.py

## Documentation Docking
`.cache/doc-docking.md` — DOCKED (CHANGELOG, docs/api.md, rendered acp.md references, manifest; README/AGENTS/SKILL template no impact).

## Follow-Up Items
Not filed — the Host's release gate is open issues = 0, so filing is left to the Host/Owner (value call):
- Cursor receipts carry `transport.cli_version: null` (empty agentInfo); the version is only obtainable from `cursor-agent --version`. Pre-existing at v0.5.7 (probe-1).
- Upgrade tier sends fast=false to Claude Fable 5.1, which advertises no fast option → limitation receipt, `fast.effective` unknown. Pre-existing.
- gpt-5.6-sol's effort id `reasoning` is not in the candidate list (value vocabulary unmeasured; design §6 out of scope).
- Carried pending-Owner items (not this run): stale non-precedent install roots (~/.cursor/skills still Grok 4.6); ~/.agents/skills now holds the candidate worker build 08eea7c (main-skill build unchanged).

## Status
READY — accepted by the Host, validated, docked; sink: merge, issue_action: close.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-135/.cache/doc-docking.md
- kaola-workflow/archive/issue-135/.cache/final-validation.md
- kaola-workflow/archive/issue-135/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-135/evidence/cursor-effort-config-id-design.md
- kaola-workflow/archive/issue-135/evidence/implementation-and-smoke.md
- kaola-workflow/archive/issue-135/evidence/probe-1-start.json
- kaola-workflow/archive/issue-135/evidence/probe-1-start.stderr
- kaola-workflow/archive/issue-135/evidence/probe-10-stop2.json
- kaola-workflow/archive/issue-135/evidence/probe-2-status-before.json
- kaola-workflow/archive/issue-135/evidence/probe-3-set-reasoning-effort-xhigh.json
- kaola-workflow/archive/issue-135/evidence/probe-4-state-after.json
- kaola-workflow/archive/issue-135/evidence/probe-5-schema-experiment.json
- kaola-workflow/archive/issue-135/evidence/probe-6-final-config-options.json
- kaola-workflow/archive/issue-135/evidence/probe-7-stop.json
- kaola-workflow/archive/issue-135/evidence/probe-8-start2.json
- kaola-workflow/archive/issue-135/evidence/probe-9-option-categories.json
- kaola-workflow/archive/issue-135/evidence/smoke-cli-version.txt
- kaola-workflow/archive/issue-135/evidence/smoke-default-stop.json
- kaola-workflow/archive/issue-135/evidence/smoke-default.json
- kaola-workflow/archive/issue-135/evidence/smoke-default.stderr
- kaola-workflow/archive/issue-135/evidence/smoke-upgrade-stop.json
- kaola-workflow/archive/issue-135/evidence/smoke-upgrade.json
- kaola-workflow/archive/issue-135/evidence/smoke-upgrade.stderr
- kaola-workflow/archive/issue-135/finalization-summary.md
- kaola-workflow/archive/issue-135/mission-ledger.jsonl
- kaola-workflow/archive/issue-135/workflow-state.md
