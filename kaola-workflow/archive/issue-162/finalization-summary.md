# Finalization Summary — issue #162

## Delivered

Running seats record the build they loaded. `status` and `list` report that build and flag restart-required drift. Every platform start, including worker starts and `~/.local/bin` starts, refuses a skewed installed Skill. `send` and `steer` refuse `seat-stale` unless `--confirm-stale` is passed, and only when the release-note file set changed. `drain-restart` waits for idle, exact-stops, and starts again; a live holder is never hot-replaced. Sibling modules load at holder startup. Release notes must say whether seats must restart. ZCode node and entry paths are facts on every locate receipt and refuse only a zcode start or resume.

Implementation commit (frozen, reviewed): `43609099a87208011d639b2bd7e7c078ed56e31c`.

The Grok Bot bridge is content stage, unpinned, `saveable: false`. This run does not tag, release, or write a pin.

Issue members:

1. Build identity on the holder record and state — `scripts/kaola-acp-holder.py`.
2. `status` and `list` report build and drift — `scripts/kaola-acp.py` `seat_freshness`.
3. Build-skew check on every platform start and `~/.local/bin` starts — `scripts/kaola-acp.py`.
4. Host refuses or confirms before dispatch — `refuse_if_stale`, `templates/orchestrator/`.
5. Drain/restart without hot rebind — `command_drain_restart`, `docs/zcode-host.md`.
6. Eager sibling load — `scripts/kaola-acp-holder.py` `load_sibling_modules`.
7. Release-note restart rule — `docs/conventions.md`, `AGENTS.md`, `CHANGELOG.md`.
8. Early ZCode path validation — `scripts/kaola-locate.py`.

## Files Changed

Product commit `4360909` (76 files). Sources: `scripts/kaola-acp.py`, `scripts/kaola-acp-holder.py`, `scripts/kaola-locate.py`, `scripts/kaola-tmux.sh`, `scripts/validate.sh`, orchestrator and delegator templates, `docs/api.md`, `docs/conventions.md`, `docs/zcode-host.md`, `AGENTS.md`, `CHANGELOG.md`, `tests/contract/test-issue-162-upgrade-safety.py`, `tests/contract/test-issue-119-host-entry.py`, `tests/contract/mock-acp-agent.py`. Generated `skills/` and `hosts/grok-bot/` come from `./scripts/render-skills.py --write`. `templates/grok-bot/accepted-revision.json` is content stage only.

## Test Coverage

- `./scripts/render-skills.py --check` — PASS (content stage, unpinned, bridge 2555 B).
- `tests/contract/test-issue-162-upgrade-safety.py` — 13/13 OK.
- `tests/contract/test-issue-119-host-entry.py` — 11/11, 160 checks.
- `tests/contract/test-issue-49-grok-bot-host.py` — 45/45 OK.
- `./scripts/validate.sh` — EXIT 0 twice on this candidate: implementer `/tmp/i162-validate2.log` and Host `/tmp/kpr162-validate-host-2.log` (123 PASS, 0 FAILED).
- claude-code review round 1 FAIL, repairs, round 2 PASS.
- Live per-platform ACP smoke was not run. Host acceptance is the offline contract gate plus review PASS.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- AGENTS.md
- CHANGELOG.md
- docs/api.md
- docs/conventions.md
- docs/zcode-host.md
- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- scripts/kaola-acp-holder.py
- scripts/kaola-acp.py
- scripts/kaola-locate.py
- scripts/kaola-tmux.sh
- scripts/validate.sh
- skills/claude-code-kaola-project-runner/references/acp.md
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-tmux.sh
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/references/acp.md
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-tmux.sh
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/references/acp.md
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-tmux.sh
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/references/acp.md
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-tmux.sh
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/references/acp.md
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-tmux.sh
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/references/acp.md
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-tmux.sh
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/references/acp.md
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-tmux.sh
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-delegator/references/handoff.md
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/host-startup.md
- skills/kaola-project-runner/references/zcode-host-dispatch.md
- skills/kimi-cli-kaola-project-runner/references/acp.md
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-tmux.sh
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/references/acp.md
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-tmux.sh
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/references/acp.md
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-tmux.sh
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/grok-bot/accepted-revision.json
- templates/kaola-delegator/references/handoff.md.tmpl
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/host-startup.md.tmpl
- templates/orchestrator/references/zcode-host-dispatch.md.tmpl
- templates/references/acp.md.tmpl
- tests/contract/mock-acp-agent.py
- tests/contract/test-issue-119-host-entry.py
- tests/contract/test-issue-162-upgrade-safety.py

## Documentation Docking

DOCKED — see `.cache/doc-docking.md`. CHANGELOG, conventions, api, zcode-host, and the AGENTS release bullet already match the behavior. README defers the command surface to `docs/api.md`. No documentation file was edited during finalization.

## Follow-Up Items

Not filed. Host acceptance recorded review round 2 notes N1–N5 as non-blocking comment content, not new claimed work and not fixes for this run:

- N1. `drain-restart` via tmux does not carry the platform default permission mode for pre-change legacy seats that have no recorded `start_selection`.
- N2. `pre_spawn_refusal` refusals (`acp-bridge-missing` / `acp-runtime-missing`) no longer carry bridge facts, and the check exists in two places.
- N3. A removed or moved recorded path, or a reinstall under a different root, goes unreported.
- N4. `kaola-quota.py`-only drift is neither `stale` nor reported.
- N5. `test_pin_drift_is_stale_without_a_skill_difference` is named against its assertion (pin drift is reported and does not set `stale`).

searched: `gh issue list --state open --search "drain-restart OR seat-stale OR runner_build OR kaola-quota drift"` — 1 hit (#162). `gh search issues` for `drain-restart permission mode`, `pre_spawn_refusal`, and `quota drift seat` in KaolaBrother/kaola-project-runner — 0 hits.

No out-of-scope drop: all 8 requested items are in the commit. No keep-open decision (`issue_action` close).

## Final Readiness Status

READY — candidate frozen at `43609099a87208011d639b2bd7e7c078ed56e31c`, validation pass recorded, Host acceptance granted (review round 2 PASS, two full validate.sh runs), docs docked. Archive and merge-sink are the next transaction. No tag, no release, no pin.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-162/.cache/doc-docking.md
- kaola-workflow/archive/issue-162/.cache/final-validation.md
- kaola-workflow/archive/issue-162/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-162/finalization-summary.md
- kaola-workflow/archive/issue-162/mission-ledger.jsonl
- kaola-workflow/archive/issue-162/workflow-state.md
