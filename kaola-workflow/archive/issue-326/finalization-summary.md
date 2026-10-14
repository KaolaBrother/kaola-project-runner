# Finalization Summary — issue-326

## Delivered

Antigravity worker `antigravity-KPR-i326-steer-settle` (antigravity/default, dispatched by the prior
claude-code Host, rebound to this ZCode Host mid-run) fixed the settle-window steer/send deadlock in
commit `1164ff38` on `workflow/issue-326` (base = main `0d4a4e50`):

1. **Settle-window steer no longer refuses with a dishonest "already settled"**: when native steer
   answers `promptRequired` while the targeted turn is still active in the holder (past its native
   result, settling), `op_steer` falls back to the holder after-turn queue — `steer_outcome:
   "queued"`, `steer_confirmation: "holder-queued"` — and the text is sent once as the next prompt
   when the turn ends. The message is not lost. When the turn has already ended, steer keeps the
   honest `not_consumed` / `steer-prompt-required` result.
2. **`prompt-in-progress` names working routes**: `steer --delivery after-turn` (new explicit
   `--delivery native|after-turn` on steer, wired through `kaola-acp.py`/`kaola-tmux.sh`) or retry
   `send` after `turn_ended`; recovery-routes updated, plus a new structured
   `prior-turn-not-completed` error when a steer followup's prior turn ends without
   `turn_completed`.
3. **Wake discipline unchanged**: `delegator_turn_wake_reason` ordering, `_delegator_followups`
   accounting, all-idle and normal queue handling untouched (verified in the Host diff review — the
   followups lines are same-text moves only).
4. Templates (`steering.md.tmpl` within its 8192 B budget), grok-bot accepted-revision (post-v0.9.12
   content stage), CHANGELOG (`## Unreleased`, `Seats: restart required`), and full renders updated.

## Candidate

Branch `workflow/issue-326`, single commit `1164ff38` over main `0d4a4e50`.
Recorder-bound hash: `9350c3b4617d4d81…`.

## Evidence

- Worker dispatch fp `becba3af…`; turn completed end_turn; delivery capture reviewed by the Host.
- Worker runs on the exact candidate: 5-suite subset PASS (42 s) and **full inventory 112 suites
  PASS (1268 s, `NO_PROXY=127.0.0.1,localhost,::1`)**; render `--write`/`--check` PASS.
- Host spot-verify on the same commit: render `--check` PASS; `test-issue-263-steer-adaptation.py`
  OK; `test-issue-65-steering.py` additions verified present (settle-window queue fallback,
  ended-turn not_consumed, prior-turn-not-completed, prompt-in-progress route naming).
- Validation record: `kaola-workflow/issue-326/.cache/final-validation.md` (verdict pass).

## Known failures and unverified scope

- `test-issue-65-steering.py` fails standalone in the Host's environment (3 no-session tests, 45 s
  `session_new_fails` timeout) — **fails identically on unmodified main `0d4a4e50`** in the same
  environment: pre-existing environment sensitivity, not candidate-caused; the worker's full run in
  its environment passed twice. No live ACP smoke this run.
- Running seats need a restart to pick up the holder change (`Seats: restart required`); no
  install performed.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- scripts/kaola-acp-holder.py
- scripts/kaola-acp.py
- scripts/kaola-recovery-routes.py
- scripts/kaola-tmux.sh
- skills/antigravity-kaola-project-runner/references/steering.md
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/antigravity-kaola-project-runner/scripts/kaola-acp.py
- skills/antigravity-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/antigravity-kaola-project-runner/scripts/kaola-tmux.sh
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/references/steering.md
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/claude-code-kaola-project-runner/scripts/kaola-tmux.sh
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/references/steering.md
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/codex-kaola-project-runner/scripts/kaola-tmux.sh
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/references/steering.md
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-tmux.sh
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/references/steering.md
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/devin-kaola-project-runner/scripts/kaola-tmux.sh
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/references/steering.md
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/droid-kaola-project-runner/scripts/kaola-tmux.sh
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/references/steering.md
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/dsh-kaola-project-runner/scripts/kaola-tmux.sh
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/references/steering.md
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/grok-kaola-project-runner/scripts/kaola-tmux.sh
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/references/steering.md
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-tmux.sh
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/references/steering.md
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/opencode-kaola-project-runner/scripts/kaola-tmux.sh
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/references/steering.md
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/zcode-kaola-project-runner/scripts/kaola-tmux.sh
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/grok-bot/accepted-revision.json
- templates/references/steering.md.tmpl
- tests/contract/test-issue-263-steer-adaptation.py
- tests/contract/test-issue-65-steering.py

## Follow-Up Items

- None filed: the settle-window behavior, routes and error are covered by the added regression
  tests in the existing 263/65-steering suites.
- searched: duplicate probe `gh issue list --state all --search "steer settle"` before the run →
  only #326 itself.

## Final readiness

Ready: candidate accepted (Host diff review + worker full inventory + host spot checks + main
comparison for the env flake), validation recorded pass, no tag/release/install performed.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-326/.cache/final-validation.md
- kaola-workflow/archive/issue-326/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-326/finalization-summary.md
- kaola-workflow/archive/issue-326/mission-ledger.jsonl
- kaola-workflow/archive/issue-326/workflow-state.md
