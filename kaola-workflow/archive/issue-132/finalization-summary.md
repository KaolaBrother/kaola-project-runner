# Finalization summary — issue-132

## Delivered
Issue #132 (design comments 1/3–3/3): one identity-verified Host per canonical root, fail-closed `host-exists` at the single shared start path (Delegator and Host paths), identity-based liveness (record + live PID + answering socket + matching holder_instance_id; never PID alone), kill-before-restart made explicit (exact-stop, proven gone, then start), and the Host-owned repo sweep triggered by a `sweep=` line on every Delegator reach-out.
- Frozen candidate efc9c0c on workflow/issue-132 (base 428e7bb); merged over main 1ad482c (#130 PTY retirement) as c034596, tree ac811be701a4625ef8a469dfad028d3ff69bfd3a (Host-approved target tree).
- Host acceptance: ACCEPT with disclosure (2026-09-22).

## Files Changed
scripts/kaola-acp.py, scripts/kaola-acp-holder.py; templates/kaola-delegator/{SKILL.md.tmpl,references/handoff.md.tmpl}; templates/orchestrator/{SKILL.md.tmpl,references/host-startup.md.tmpl,references/zcode-host-dispatch.md.tmpl}; README.md, CHANGELOG.md, docs/api.md, docs/zcode-host.md, docs/acp-watch/list-view.md; tests/contract/{test-acp-contract.py,test-issue-74-kaola-delegator.py,test-generated-skills.py}; rendered skills/ and hosts/ copies.

## Test Coverage
T1–T13 asserted (T5/T13 in test-issue-74 ZCode sandbox, T6 in test-acp-contract): Issue132HolderIdentityTests + Issue132AnchorUnitTests (16), test_one_host_per_repo_refuses_host_exists (27 checks incl. F1 silent-Host block), check_issue_132_one_host (T10/T11 pins). Each repair round's guard mutation-checked (reverting the fix turns its test red). T12 budgets via render --check / progressive-disclosure. T14 (live UAT) not run — Host will verify read-only live after the release reinstall.

## Validation
- final-validation: `.cache/final-validation.md` verdict pass, validated_candidate_hash 7807130f…ccf56 (tree ac811be).
- c034596 (integration): render-skills.py --check rc=0; validate.sh rc=0, 495 s, sweep residual_pids [] (`.cache/validate-integ-c034596.log`); git diff --check 1ad482c..c034596 rc=0.
- efc9c0c (frozen candidate): render --check rc=0; validate.sh rc=0, 510 s (`.cache/validate-efc9c0c.log`).
- Superseded, not passes: validate on 38056e7 and 83052ce died with their sessions (no validate_rc line).
- run-chains: chains_config_missing — consumer repo (no test:kaola-workflow:* scripts); finalize gates on the recorded final-validation (#475).
- Review chain (clean-context, not the implementer): afeb43b → 0H/3M/4L; edc4322 → 2M (N1,N2) + lows; 38056e7 → 1M (M1) + lows; 83052ce → 1M (M2) + L3; efc9c0c → 0H/0M/1L/1I. Reports in `.cache/review-*.md`.

## Changed Paths
finalize --check reported 45 source-scoped paths (validation: chains_green, ok: true); it omits docs (README.md, CHANGELOG.md, docs/*, listed under Files Changed):
- scripts/kaola-acp-holder.py
- scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-delegator/SKILL.md
- skills/kaola-delegator/references/handoff.md
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/host-startup.md
- skills/kaola-project-runner/references/zcode-host-dispatch.md
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/kaola-delegator/SKILL.md.tmpl
- templates/kaola-delegator/references/handoff.md.tmpl
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/host-startup.md.tmpl
- templates/orchestrator/references/zcode-host-dispatch.md.tmpl
- tests/contract/test-acp-contract.py
- tests/contract/test-generated-skills.py
- tests/contract/test-issue-74-kaola-delegator.py

## Documentation Docking
`.cache/doc-docking.md` — DOCKED.

## Follow-Up Items (disclosed, Host-ruled accept; decisions for the Host/Owner)
- L4 (low, errs-safe): holder and caller in different time zones + agent started in the repeated DST hour → agent group left unswept. Thorough fix: read libproc `start_tvsec` on both sides.
- docs/api.md "time zones do not matter" wording is slightly absolute (L4).
- I4 (info): 83052ce-era string agent_started trusted (never released).
- #130-side L2/L3/§7 items (Host-listed follow-up decisions).
- Recorded deviations kept (round-1 accepted): `--include-dead` opt-in (frozen list contract), reused-PID record retirement, holder `dispatcher` field; C11 skipped by design.
- T14 live UAT: Host, after release reinstall.

## Readiness
READY — accepted, target tree approved, final validation recorded.
