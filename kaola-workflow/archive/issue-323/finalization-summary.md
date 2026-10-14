# Finalization summary — issue-323

## Delivered

The **antigravity** (agy) runtime as the eleventh worker platform, per the
owner's final two-tier spec.

- **Two tiers** (owner supersession 2026-10-14 16:11):
  - `antigravity/default` → `gemini-4-argon-medium`, class Elite,
    profile: "High-throughput, multimodal agentic implementer. Think
    senior generalist engineer, strong on coding, long context, and
    parallel agent work, with a real creative streak in interactive
    front-end and 3D. Best with a clear brief and a defined done."
  - `antigravity/xhigh` → `gemini-4-argon-high`, class Elite, profile:
    "Escalation level: use it when Argon medium cannot solve the task,
    especially hard debugging that needs a root-cause fix or long
    multi-step work. Slower and uses more quota."
- **In-repo ACP wrapper** `scripts/kaola-antigravity-acp.py`: bridges
  ACP to agy's headless stream-json protocol (one child per session,
  `--conversation` resume, SIGINT cancel, leading-`/` refused, no
  native mid-turn steer → `steering_delivery: after-turn`). Effort is
  baked into the model slug; `--effort` is never passed. An
  unsigned/ineligible account maps to the recoverable `login-required`
  refusal with agy's verify URL in the receipt (#309).
- **Registration**: kaola-acp, quota (one `account` package, windows
  unknown → unverified), locate, model-policy, grok-bot-verify, tmux,
  render-skills, install-local; README Elite count 16 / 25 presets;
  AGENTS.md platform table updated.
- **Live acceptance** (agy 1.3.5, signed-in account): one-turn reply;
  second turn on the same session (remembered the first answer); stop;
  `start --resume <native id>` and a third turn that still remembered;
  an xhigh-tier turn. Live finding: the conversation id announced at
  start is provisional (the start child is replaced before the first
  prompt when mode is applied); the last `native_session_identity` is
  the resumable one — documented in the manifest/README/CHANGELOG.
  Steer and cancel remain unmeasured live (stated honestly).
- **Tests**: new `test-issue-323-antigravity-acp.py` (offline mock-agy
  plus the real Runner and holder; two-tier pins; xhigh through the
  real Runner; provisional-id regression; cleanup that stops
  error-state holders); enumeration pins in existing suites updated for
  the eleventh platform.

## Candidate

- Commits `0139c823` (base platform + wrapper + registration) and
  `55188a35` (owner supersession: two tiers + final profiles + live
  acceptance) on `workflow/issue-323` (worktree
  `.kw/worktrees/issue-323`, base `32fda22a`). Implemented by the
  `claude-code/sonnet` seat `claude-code-KPR-i323-antigravity` (owner
  temp grant); reviewed and finalized by the Host.

## Evidence

- Host diff review (this run): yaml exactly per the owner's final
  spec; live acceptance through the ACP wrapper on the signed-in
  account; provisional-id finding honestly documented.
- `./scripts/render-skills.py --check` — PASS.
- Affected suites, all exit 0: `test-issue-323-antigravity-acp.py`
  (new), `test-acp-contract.py`, `test-generated-skills.py`,
  `test-issue-218-preset-ids.py`, `test-issue-244-dispatch.py`,
  `test-progressive-disclosure.py`, `test-issue-148-quota-packages.py`
  (logs `/tmp/kpr-i323-*.log`).
- `.cache/final-validation.md`: verdict `pass`, candidate hash
  `f71dd3f1862a73f6…`.
- Worker seat exact-stopped after acceptance (`state: stopped`).

## Known failures / unverified scope

- Live steer and SIGINT-cancel behavior unmeasured (stated in the
  commit and docs). Quota window shape unverified. Full inventory
  after merge. No release (owner releases).

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
- docs/grok-bot-host.md
- docs/zcode-host.md
- platforms/antigravity.yaml
- scripts/adapters/antigravity.sh
- scripts/install-local.sh
- scripts/kaola-acp.py
- scripts/kaola-antigravity-acp.py
- scripts/kaola-grok-bot-verify.py
- scripts/kaola-locate.py
- scripts/kaola-model-policy.py
- scripts/kaola-quota.py
- scripts/kaola-tmux.sh
- scripts/render-skills.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/.generated-by-kaola-project-runner
- skills/antigravity-kaola-project-runner/SKILL.md
- skills/antigravity-kaola-project-runner/agents/openai.yaml
- skills/antigravity-kaola-project-runner/references/acp.md
- skills/antigravity-kaola-project-runner/references/platform.md
- skills/antigravity-kaola-project-runner/references/steering.md
- skills/antigravity-kaola-project-runner/scripts/adapters/antigravity.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-paths.py
- skills/antigravity-kaola-project-runner/scripts/kaola-acp.py
- skills/antigravity-kaola-project-runner/scripts/kaola-antigravity-acp.py
- skills/antigravity-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/antigravity-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/antigravity-kaola-project-runner/scripts/kaola-model-policy.py
- skills/antigravity-kaola-project-runner/scripts/kaola-project-compact-notice.py
- skills/antigravity-kaola-project-runner/scripts/kaola-quota.py
- skills/antigravity-kaola-project-runner/scripts/kaola-record-contract.py
- skills/antigravity-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/antigravity-kaola-project-runner/scripts/kaola-session-names.py
- skills/antigravity-kaola-project-runner/scripts/kaola-tmux.sh
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/antigravity-kaola-project-runner/scripts/platform.yaml
- skills/antigravity-kaola-project-runner/scripts/runtime-tmux.sh
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-model-policy.py
- skills/claude-code-kaola-project-runner/scripts/kaola-quota.py
- skills/claude-code-kaola-project-runner/scripts/kaola-tmux.sh
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-model-policy.py
- skills/codex-kaola-project-runner/scripts/kaola-quota.py
- skills/codex-kaola-project-runner/scripts/kaola-tmux.sh
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
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
- skills/kaola-delegator/references/host-platforms.md
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/agents/openai.yaml
- skills/kaola-project-runner/references/host-entry-matrix.md
- skills/kaola-project-runner/references/profile-catalog.md
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
- templates/kaola-delegator/references/host-platforms.md.tmpl
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/host-entry-matrix.md
- tests/contract/mock-agy.py
- tests/contract/test-generated-skills.py
- tests/contract/test-installer-migration.sh
- tests/contract/test-installer-runtimes.sh
- tests/contract/test-issue-119-host-entry.py
- tests/contract/test-issue-123-shared-refs.py
- tests/contract/test-issue-147-installed-survey.py
- tests/contract/test-issue-148-quota-packages.py
- tests/contract/test-issue-187-delegator-any-host.py
- tests/contract/test-issue-215-install-truthfulness.py
- tests/contract/test-issue-218-preset-ids.py
- tests/contract/test-issue-259-record-contract.py
- tests/contract/test-issue-313-name-advisory.py
- tests/contract/test-issue-323-antigravity-acp.py
- tests/contract/test-issue-41-orchestrator.py
- tests/contract/test-issue-49-grok-bot-host.py
- tests/contract/test-issue-50-runner-integration.py
- tests/contract/test-issue-65-steering.py
- tests/contract/test-issue-78-heredoc-deadlock.py

## Follow-Up Items

- KT five-item answer to be posted by the Host as a follow-up comment
  on #323.

## Final readiness

Ready: candidate reviewed, affected scope green, validation recorded,
live acceptance passed. Proceed to sink (merge), KT answers, and close.
