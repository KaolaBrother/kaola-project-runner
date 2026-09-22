# Finalization summary — bundle-140 (#140)

## Delivered
Owner-decided MAX-PATH design (2026-09-23): Devin CLI 3000.11.1 rejects every preset on the ACP
`model` option (-32602) and silently runs `swe-2-high`, but `devin acp --model <id>` sets the
session model. The original strong presets are kept and delivered through spawn argv.
- `platforms/devin.yaml`: `acp_command_default/_upgrade/_alt` = `devin acp --model <preset id>`
  (`swe-2-max`, `fusion-claude-fable-5-1-high-sidekick-swe-2-medium`, `claude-fable-5-1-high`);
  base `acp_command` unchanged; `acp_verified_versions` → `cli=3000.11.1`; `acp_quirks` updated.
- `scripts/kaola-acp.py`: spawn command precedence `--command` > `KAOLA_ACP_COMMAND` > tier command
  > `acp_command`, the tier command only when the tier preset selects the model (explicit
  `--model` / preserved resume keep the base). A model the argv already carries is not re-sent:
  `config_application.model.applied_via: argv`; `effective_selection` reports it as
  `effective_model_source: launch-argv` beside the stale `advertised_model`.
- `scripts/render-skills.py`: the three keys are OPTIONAL (non-empty; `_alt` needs a label); the
  other nine manifests are untouched.
- The earlier swe-2-high downgrade mapping (comment 5779572092) was superseded by Owner correction
  and never landed; evidence comment 5780681827 records the design and proofs.

## Files Changed
platforms/devin.yaml; scripts/kaola-acp.py; scripts/render-skills.py; templates/references/acp.md.tmpl;
tests/contract/test-acp-contract.py; tests/contract/test-issue-111-model-tiers.py; CHANGELOG.md;
docs/api.md; generated skills/*/references/acp.md, skills/*/scripts/kaola-acp.py (10 workers),
skills/devin-kaola-project-runner/scripts/platform.yaml.

## Test Coverage
- test-issue-111-model-tiers.py `TierAgentCommand`: devin tier commands carry the original preset
  ids; explicit `--model` and preserved resume keep the base; all nine other platforms declare no
  tier command and no argv `--model`; render rejects empty / unlabelled tier commands.
- test-acp-contract.py Issue34: argv-carried model skips the option apply (fake agent with stale
  `currentValue`), and a model not in the argv still goes through the option (path unchanged).

## Validation
- `./scripts/render-skills.py --write` then `--check` — PASS (budgets OK)
- `./scripts/validate.sh` — rc=0 at 9df0d42, and again at 0c879b7 (final candidate, log validate-140.log, 40 suites OK, 0 FAIL/ERROR)
- `git diff --check c3959da 0c879b7` — clean
- Record: .cache/final-validation.md, validated_candidate_hash 91d17b62c850…
- Live acceptance (real Runner path, worktree build 9df0d42, /tmp/kpr-i140-probe/, KAOLA_ACP_* unset):
  default `swe-2-max` (sessions.db noble-towel), upgrade `fusion-claude-fable-5-1-high-sidekick-swe-2-medium`
  (concise-cycle), fable `claude-fable-5-1-high` (walnut-edam); each `applied_via: argv`, send
  `turn_completed`, stop `residual_pids: []`. 5f1939d/0c879b7 are docs-only after the probes.
- Host acceptance: ACCEPTED at 9df0d42 (2026-09-23).

## Changed Paths
- CHANGELOG.md
- docs/api.md
- platforms/devin.yaml
- scripts/kaola-acp.py
- scripts/render-skills.py
- skills/claude-code-kaola-project-runner/references/acp.md
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/references/acp.md
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/references/acp.md
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/references/acp.md
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/platform.yaml
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
- tests/contract/test-acp-contract.py
- tests/contract/test-issue-111-model-tiers.py

## Issue walk
- `--tier default` does not land `swe-2-max` on 11.1 → spawn argv `--model swe-2-max`; live probe + sessions.db.
- Same failure on upgrade/fable (comment 5778745334) → per-tier argv commands; live probes.
- Silent substitution / "surface -32602" direction → redundant apply skipped; receipt names
  `applied_via: argv` and keeps the stale `advertised_model`; fake-agent tests.
- `acp_verified_versions` unmeasured drift → `cli=3000.11.1`.

## Documentation Docking
DOCKED — see .cache/doc-docking.md.

## Follow-Up Items
- No new defects discovered; no follow-up issue filed. v0.5.8 release (tag → pin → re-pin) is the Host's next step, not this run.

## Readiness
READY — closure decision: close #140.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/bundle-140/.cache/doc-docking.md
- kaola-workflow/archive/bundle-140/.cache/final-validation.md
- kaola-workflow/archive/bundle-140/.cache/origin/selection-record.json
- kaola-workflow/archive/bundle-140/finalization-summary.md
- kaola-workflow/archive/bundle-140/mission-ledger.jsonl
- kaola-workflow/archive/bundle-140/workflow-state.md
