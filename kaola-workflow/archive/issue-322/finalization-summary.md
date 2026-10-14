# Finalization summary — issue-322

## Delivered

Fix for #322: Grok 4.7 seat tiers changed per the owner decision.

- `platforms/grok.yaml`: `grok/default` → Grok 4.7 at
  `reasoning_effort=high` (was xhigh); new named tier `xhigh` → Grok
  4.7 at `reasoning_effort=xhigh`, **Elite** class, profile text:
  "Escalation level: use it when the Grok Build default (Grok 4.7
  high) cannot solve the task." (the only new profile text; no
  existing text changed).
- `platforms/cursor-cli.yaml`: `cursor-cli/default` → `grok-4.7-high`
  (was `grok-4.7-xhigh`); `cursor-cli/opus` (`claude-opus-5-5-high`)
  unchanged; `acp_model_map` keeps the `grok-4.7-xhigh` entries for
  backward compatibility (explicit xhigh still decomposes).
- `scripts/adapters/cursor-cli.sh`, `scripts/adapters/grok.sh`,
  `scripts/kaola-acp.py` (hard-coded model id): updated to the new
  default; renders via `render-skills.py`; README, AGENTS.md,
  `docs/conventions.md` tier mentions updated.
- Tests: new `test_grok_default_and_xhigh_tiers_send_their_declared_effort`
  (default sends high not xhigh; `--tier xhigh` sends preset
  `grok/xhigh` with effort xhigh) and
  `test_cursor_explicit_xhigh_model_id_still_decomposes` in
  `test-acp-contract.py`; updated expectations in `test-issue-148`,
  `test-issue-218-preset-ids` (pins the new tier and Elite/total
  counts), `test-issue-244`, `test-lifecycle-contract`,
  `test-generated-skills`.

## Live verification (owner acceptance)

40-line JSON-RPC client in /tmp (initialize + session/new +
session/set_config_option, no prompt, no work, scratch repo deleted):

- **grok CLI 1.0.52** (`grok agent --always-approve stdio`): session/new
  advertised `reasoning_effort` values `xhigh, high, medium, low`;
  `set model=grok-4.7` ok; **`set reasoning_effort=high` ok, returned
  config shows `reasoning_effort` current `high`**. (The native default
  is xhigh, so the explicit high selection is what makes the preset
  honest.)
- **cursor-agent 2026.10.01-e373342** (`cursor-agent --yolo acp`,
  `parameterizedModelPicker=true`): session/new advertised model
  `grok-4.7` and `reasoning_effort` values `low, medium, high, xhigh`;
  `set model=grok-4.7` ok; **`set reasoning_effort=high` ok** (the
  persisted effort was already high, proving acceptance but not a
  visible value change — stated honestly).

## Candidate

- Commits `c3a94d2a` (content-cycle opener) + `74dd7805` (feat, 48
  files) on `workflow/issue-322` (worktree `.kw/worktrees/issue-322`,
  base `3f4bb5ef`). Implemented by the `claude-code/sonnet` seat
  `claude-code-KPR-i322-tier-high` (owner temp grant, Grok 402
  bypass); reviewed and finalized by the Host.

## Evidence

- Host diff review (this run): yaml shape exactly per owner; no
  existing profile text changed (verified diff); backward-compatible
  xhigh cursor entries kept; live evidence genuine and honestly
  stated.
- `./scripts/render-skills.py --check` — PASS.
- Affected suites, all exit 0: `test-acp-contract.py` (87 tests),
  `test-generated-skills.py`, `test-issue-148-quota-packages.py`,
  `test-issue-218-preset-ids.py`, `test-issue-244-dispatch.py`,
  `test-lifecycle-contract.py`, `test-progressive-disclosure.py`,
  `test-issue-295-delegator-seats.py` (logs `/tmp/kpr-i322-*.log`).
- `.cache/final-validation.md`: verdict `pass`, candidate hash
  `abf42b9a11e2a0ca…`.
- Worker seat exact-stopped after acceptance (`state: stopped`).

## Known failures / unverified scope

- Full inventory after merge. `acp_verified_versions` not bumped
  (probes covered the config-option step only, not a full start/send
  smoke). Cursor catalog listing of `grok-4.7-high-fast` declared but
  not tested. No release (owner releases).

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
- docs/conventions.md
- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- platforms/cursor-cli.yaml
- platforms/grok.yaml
- scripts/adapters/cursor-cli.sh
- scripts/adapters/grok.sh
- scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/SKILL.md
- skills/cursor-cli-kaola-project-runner/references/platform.md
- skills/cursor-cli-kaola-project-runner/scripts/adapters/cursor-cli.sh
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/platform.yaml
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/SKILL.md
- skills/grok-kaola-project-runner/references/platform.md
- skills/grok-kaola-project-runner/scripts/adapters/grok.sh
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/platform.yaml
- skills/kaola-project-runner/references/profile-catalog.md
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/grok-bot/accepted-revision.json
- tests/contract/test-acp-contract.py
- tests/contract/test-generated-skills.py
- tests/contract/test-issue-148-quota-packages.py
- tests/contract/test-issue-218-preset-ids.py
- tests/contract/test-issue-244-dispatch.py
- tests/contract/test-lifecycle-contract.py

## Follow-Up Items

- None.

## Final readiness

Ready: candidate reviewed, affected scope green, validation recorded,
live evidence in hand. Proceed to sink (merge) and archive.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-322/finalization-summary.md
