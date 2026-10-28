# Finalization Summary — issue-416

## Delivered
Hermes Agent (`hermes`) as KPR's twelfth worker platform, offline only (#416, #415 phases 1+3):
- `platforms/hermes.yaml`, `scripts/adapters/hermes.sh`, the in-repo Option A ACP adapter
  `scripts/kaola-hermes-acp.py` (launches `hermes --yolo acp`, never `--accept-hooks`; maps the
  `model`/`mode` config options to `session/set_model`/`session/set_mode`; refuses other configIds;
  resume via `session/load` with a refusal on a null or mismatched result; a recoverable
  `login-required` route naming `hermes acp --setup` / `hermes model`).
- Registration in render-skills, kaola-acp, kaola-locate, kaola-quota, kaola-model-policy,
  kaola-grok-bot-verify, kaola-tmux.sh and install-local.sh; the rendered
  `skills/hermes-kaola-project-runner/`; platform-count docs; README Hermes note, Host-capability
  row and the corrected per-preset Worker grant text (#346).
- Catalog: `hermes/default` (effort=high) and `hermes/max` (escalation, effort=max), both Worker,
  per owner comment `owner-hermes-tiers-high-max-autoescalate-20261028` (Host-approved). Effort is
  not ACP-applied and is reported as not applied.
- New offline suite `tests/contract/test-issue-416-hermes-acp.py` with
  `tests/contract/fake-hermes-acp-agent.py`, registered in `python_suites_all` and `python_suites_b`.

## Candidate
- `0d3189b1` (implementation) + `4e8985f7` (Host-ordered repair: the no-Hermes-grant guard scans
  real grant rows; re-measure recorded as the Host decision). Branch `workflow/issue-416`, base
  `f6bed999`.

## Acceptance
- Host verdict: ACCEPTED (repair `4e8985f7` verified independently by the Host: test-issue-416
  exit 0, render-skills.py --check PASS, 12 workers).
- Host decisions: `reference_bytes` 9216 -> 10240 re-measure APPROVED (#413 precedent; recorded in
  `templates/budgets.json` `_comment` and the #68/#72 guards); Hermes tiers catalog-only per the
  owner comment.
- No `worker_grants` row or other authorization record added (Hermes seat count stays 0);
  `templates/grok-golden/` diff empty; `.kaola/` untouched; no release, tag or pin.

## Evidence
- Final validation on `4e8985f7`: `./scripts/render-skills.py --check && ./scripts/validate.sh
  --suite test-issue-416-hermes-acp.py --suite test-issue-68-heartbeat-snapshot.py --suite
  test-issue-72-session-naming.py` — PASS (21/21, 16/16, 8/8); log `/tmp/kpr416-final-suites.log`;
  record `.cache/final-validation.md`.
- Candidate `0d3189b1` affected-suite run (28 suites through `validate.sh --suite`): all pass except
  the two pre-existing base failures below. Install (`--platform hermes`; default 14/14), `survey`
  (hermes present) and `kaola-locate.py --worker hermes` verified.

## Known failures or unverified scope
- Pre-existing, not caused by this run: `test-acp-contract.py` 1 failure (identical on base) and
  `test-issue-244-dispatch.py` 9 failures (a subset of the base's 15). Filed as #420.
- No live ACP session was started (offline scope). Live measurement, the provider read-back,
  `--yolo` effect on the gateway-owned session, steer, and stop proof belong to #417. CHANGELOG,
  version, tag and pin belong to #418.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- AGENTS.md
- CHANGELOG.md
- README.md
- docs/api.md
- docs/architecture.md
- docs/codex-host.md
- docs/conventions.md
- docs/zcode-host.md
- platforms/codex.yaml
- platforms/hermes.yaml
- scripts/adapters/codex.sh
- scripts/adapters/hermes.sh
- scripts/install-local.sh
- scripts/kaola-acp.py
- scripts/kaola-grok-bot-verify.py
- scripts/kaola-hermes-acp.py
- scripts/kaola-locate.py
- scripts/kaola-model-policy.py
- scripts/kaola-quota.py
- scripts/kaola-tmux.sh
- scripts/render-skills.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-acp.py
- skills/antigravity-kaola-project-runner/scripts/kaola-model-policy.py
- skills/antigravity-kaola-project-runner/scripts/kaola-quota.py
- skills/antigravity-kaola-project-runner/scripts/kaola-tmux.sh
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-model-policy.py
- skills/claude-code-kaola-project-runner/scripts/kaola-quota.py
- skills/claude-code-kaola-project-runner/scripts/kaola-tmux.sh
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/SKILL.md
- skills/codex-kaola-project-runner/references/platform.md
- skills/codex-kaola-project-runner/scripts/adapters/codex.sh
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-model-policy.py
- skills/codex-kaola-project-runner/scripts/kaola-quota.py
- skills/codex-kaola-project-runner/scripts/kaola-tmux.sh
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/platform.yaml
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-model-policy.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-quota.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-tmux.sh
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-model-policy.py
- skills/devin-kaola-project-runner/scripts/kaola-quota.py
- skills/devin-kaola-project-runner/scripts/kaola-tmux.sh
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-model-policy.py
- skills/droid-kaola-project-runner/scripts/kaola-quota.py
- skills/droid-kaola-project-runner/scripts/kaola-tmux.sh
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-model-policy.py
- skills/dsh-kaola-project-runner/scripts/kaola-quota.py
- skills/dsh-kaola-project-runner/scripts/kaola-tmux.sh
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-model-policy.py
- skills/grok-kaola-project-runner/scripts/kaola-quota.py
- skills/grok-kaola-project-runner/scripts/kaola-tmux.sh
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/hermes-kaola-project-runner/.generated-by-kaola-project-runner
- skills/hermes-kaola-project-runner/SKILL.md
- skills/hermes-kaola-project-runner/agents/openai.yaml
- skills/hermes-kaola-project-runner/references/acp.md
- skills/hermes-kaola-project-runner/references/platform.md
- skills/hermes-kaola-project-runner/references/steering.md
- skills/hermes-kaola-project-runner/scripts/adapters/hermes.sh
- skills/hermes-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/hermes-kaola-project-runner/scripts/kaola-acp-paths.py
- skills/hermes-kaola-project-runner/scripts/kaola-acp.py
- skills/hermes-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/hermes-kaola-project-runner/scripts/kaola-cwd-guard.py
- skills/hermes-kaola-project-runner/scripts/kaola-hermes-acp.py
- skills/hermes-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/hermes-kaola-project-runner/scripts/kaola-model-policy.py
- skills/hermes-kaola-project-runner/scripts/kaola-project-compact-notice.py
- skills/hermes-kaola-project-runner/scripts/kaola-quota.py
- skills/hermes-kaola-project-runner/scripts/kaola-record-contract.py
- skills/hermes-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/hermes-kaola-project-runner/scripts/kaola-session-names.py
- skills/hermes-kaola-project-runner/scripts/kaola-tmux.sh
- skills/hermes-kaola-project-runner/scripts/main-skill-build.json
- skills/hermes-kaola-project-runner/scripts/platform.yaml
- skills/hermes-kaola-project-runner/scripts/runtime-tmux.sh
- skills/kaola-delegator/references/host-platforms.md
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/agents/openai.yaml
- skills/kaola-project-runner/references/host-entry-matrix.md
- skills/kaola-project-runner/references/profile-catalog.md
- skills/kaola-project-runner/references/worker-profiles.md
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-model-policy.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-quota.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-tmux.sh
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-model-policy.py
- skills/opencode-kaola-project-runner/scripts/kaola-quota.py
- skills/opencode-kaola-project-runner/scripts/kaola-tmux.sh
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-model-policy.py
- skills/zcode-kaola-project-runner/scripts/kaola-quota.py
- skills/zcode-kaola-project-runner/scripts/kaola-tmux.sh
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/budgets.json
- templates/orchestrator/references/host-entry-matrix.md
- tests/contract/fake-hermes-acp-agent.py
- tests/contract/test-generated-skills.py
- tests/contract/test-installer-migration.sh
- tests/contract/test-installer-runtimes.sh
- tests/contract/test-issue-111-model-tiers.py
- tests/contract/test-issue-119-host-entry.py
- tests/contract/test-issue-123-shared-refs.py
- tests/contract/test-issue-147-installed-survey.py
- tests/contract/test-issue-148-quota-packages.py
- tests/contract/test-issue-187-delegator-any-host.py
- tests/contract/test-issue-215-install-truthfulness.py
- tests/contract/test-issue-218-preset-ids.py
- tests/contract/test-issue-237-model-display.py
- tests/contract/test-issue-244-dispatch.py
- tests/contract/test-issue-259-record-contract.py
- tests/contract/test-issue-313-name-advisory.py
- tests/contract/test-issue-323-antigravity-acp.py
- tests/contract/test-issue-345-worker-pool.py
- tests/contract/test-issue-346-worker-grants.py
- tests/contract/test-issue-350-computer-use-roles.py
- tests/contract/test-issue-351-dsh-profile.py
- tests/contract/test-issue-41-orchestrator.py
- tests/contract/test-issue-416-hermes-acp.py
- tests/contract/test-issue-49-grok-bot-host.py
- tests/contract/test-issue-65-steering.py
- tests/contract/test-issue-68-heartbeat-snapshot.py
- tests/contract/test-issue-72-session-naming.py
- tests/contract/test-issue-78-heredoc-deadlock.py

## Follow-Up Items
- filed: #420 — pre-existing red suites on main (test-acp-contract stale `GPT-6 Luna` pin;
  test-issue-244-dispatch 9 admission failures). Labels `bug`, `P2`. Confirmed: open, body
  non-empty (2136 chars).
- #417 (live measurement) and #418 (release) remain open and unchanged by this run.

## Readiness
Ready to sink: candidate accepted, validation recorded, closure decision `close`.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-416/.cache/final-validation.md
- kaola-workflow/archive/issue-416/finalization-summary.md
- kaola-workflow/archive/issue-416/mission-ledger.jsonl
- kaola-workflow/archive/issue-416/workflow-state.md
