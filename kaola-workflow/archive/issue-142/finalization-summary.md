# Finalization summary — issue-142 (#142)

## Delivered
Codex platform `default` tier moved from GPT-5.6 Sol High (`gpt-5.6-sol`, effort=high) to **GPT-6 Sol**
(`gpt-6-sol`), per the measured load path in issue comment 5787391815 (Owner-reopened with live evidence):
- `default_model_name: "GPT-6 Sol"`, `default_model_id: "gpt-6-sol"`.
- `default_model_parameters: "no Runner effort override"`, `default_model_effort: ""` — gpt-6-sol advertises no
  effort option on the pinned ACP surface (`reasoning_effort` rejected -32602 for high and medium), so the preset
  claims no applied effort (droid/dsh wording precedent; renderer accepts it, no human decision needed).
- `acp_effort_config_id` stays `reasoning_effort`; an explicit `--effort` under gpt-6-sol stays a limitation receipt.
- Upgrade tier (`gpt-6-astra`/high), alt none, `acp_verified_versions`, npx pins, `CODEX_PATH` unchanged.

## Files Changed
platforms/codex.yaml; scripts/adapters/codex.sh; generated skills/codex-kaola-project-runner/{SKILL.md,
references/platform.md,scripts/adapters/codex.sh,scripts/platform.yaml}; tests/contract/{mock-acp-agent.py,
test-acp-contract.py,test-generated-skills.py,test-issue-130-pty-retired.py}; CHANGELOG.md.

## Test Coverage
- test-acp-contract.py: `test_codex_default_applies_model_fast_mode_in_order_without_effort` — default start sends
  exactly model=gpt-6-sol, fast-mode=off, mode=agent-full-access (no reasoning_effort); effort `applied` false with
  reason `no-resolved-value`; resolved_model gpt-6-sol. Preflight test asserts gpt-6-sol advertised and resolved.
- mock-acp-agent.py: codex model option gains `gpt-6-sol` "6 Sol" (the measured post-apply catalog value).
- test-generated-skills.py: codex leakage token gpt-5.6-sol -> gpt-6-sol.
- test-issue-130-pty-retired.py: mismatch fixture resolved_runtime_model_id -> gpt-6-sol.

## Validation
- `./scripts/render-skills.py --check` — PASS rc=0 (budgets OK) on 0415d2a (rebased onto main 992da2c).
- `./scripts/validate.sh` — rc=0 on 0415d2a in 517 s: 40 suite runs, 283 `ok`, no FAIL/ERROR/Traceback,
  kaola-grok-bot-verify PASS, sweep `residual_pids: []` (log validate-142.log).
- `git diff --check main..HEAD` — clean.
- Record: .cache/final-validation.md, validated_candidate_hash 35b18506e6d0…
- Host acceptance: ACCEPTED at 615d8fe (pre-rebase; Host re-ran --check and validate.sh rc=0); the rebase onto
  992da2c only re-ordered the CHANGELOG Unreleased entry after the landed #143/#144 entries, and both gates were
  re-run green on the rebased tip 0415d2a.
- Not executed in this run: post-merge live `--tier default` receipt (`resolved_model=gpt-6-sol`,
  `effective_model=gpt-6-sol`, effort limitation) — Host-owned after sink + install refresh. Pre-change live proof
  of the apply is in issue comment 5787391815 (pinned npx @openai/codex@0.153.4 + codex-acp@1.11.0, 2026-09-23).

## Changed Paths
- CHANGELOG.md
- platforms/codex.yaml
- scripts/adapters/codex.sh
- skills/codex-kaola-project-runner/SKILL.md
- skills/codex-kaola-project-runner/references/platform.md
- skills/codex-kaola-project-runner/scripts/adapters/codex.sh
- skills/codex-kaola-project-runner/scripts/platform.yaml
- tests/contract/mock-acp-agent.py
- tests/contract/test-acp-contract.py
- tests/contract/test-generated-skills.py
- tests/contract/test-issue-130-pty-retired.py

## Issue walk
- Body blocked on "no 6 Sol in catalog"; comment 5787391815 (later, wins) measured gpt-6-sol loads via plain ACP
  model set with no settable effort and proposed the landing — implemented as proposed.
- platforms/codex.yaml default id/name/parameters -> done; scripts/adapters/codex.sh aligned -> done.
- scripts/kaola-model-policy.py: no codex default reference (only TUI-row parsing comments naming gpt-6-astra) -> no change.
- skills re-rendered -> --check PASS. Tests (test-acp-contract, test-generated-skills, mock agent; body's
  test-model-policy.sh does not exist in tests/contract) -> updated. CHANGELOG -> entry.
- acp_verified_versions unchanged -> confirmed in diff.
- Live `--tier default` receipt -> Host-owned post-merge (see Validation).

## Documentation Docking
.cache/doc-docking.md — DOCKED.

## Follow-Up Items
None filed. No run-discovered defect.

## Status
READY — accepted; finalize + merge sink.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-142/.cache/doc-docking.md
- kaola-workflow/archive/issue-142/.cache/final-validation.md
- kaola-workflow/archive/issue-142/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-142/finalization-summary.md
- kaola-workflow/archive/issue-142/mission-ledger.jsonl
- kaola-workflow/archive/issue-142/workflow-state.md
