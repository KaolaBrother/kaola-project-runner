# Finalization summary — issue-309

## Delivered

Fix for #309: no reported failure is a dead end — every audited
runner refusal carries a recovery route (the next command) or an
explicit agent self-route with the context that choice needs.

- `scripts/kaola-recovery-routes.py` (new, 478 lines): the `ROUTES`
  table mapping every audited failure/refusal code to
  `(route|self-route, text)`, and the stamp that attaches the text to
  refusal receipts. Surfaces audited: `kaola-acp.py`,
  `kaola-launchd-broker.py`, `kaola-locate.py`, `install-local.sh`,
  `kaola-tmux.sh`, `kaola-grok-bot-verify.py`, `kaola-dispatch.py`
  (which already carried typed `recovery` fields — reused, not
  duplicated).
- The broker dead-end text ("reconcile it" with no route) is gone: the
  unowned-exited-job route names exact-stop → `attest --intent resume`
  → `start --resume`, and composes with #308's auto-reap (landed
  separately; this branch's base predates it — the integrated tree
  carries both).
- The owner's concrete Host-restart route (2026-10-12T10:35Z) is
  documented in the Delegator skill source:
  `templates/kaola-delegator/references/host-restart.md` — when a Host
  session cannot be resumed, the Delegator may start a FRESH Host and
  hand it a summary of the previous session (goals, decisions,
  in-flight tasks, live seats and their holders, pending items), built
  from the exact receipt-producing commands (status, capture, list,
  delegator view); the new Host re-adopts live seats; leftover broker
  state cleans via the runner's own commands.
- Tests: `test-issue-309-recovery-routes.py` (8 cases, 253 lines):
  every code extracted from the audited surfaces has a route (the
  enumeration is extracted, not hand-maintained); the stamp attaches
  table text and keeps success/recovery fields unstamped; oversized
  attest receipts keep the route; shell and install texts match the
  table; dynamic capture codes and the webhook tuple covered; the
  broker dead end is gone and the holder process is not stamped;
  host-restart docs and registry consistent.
- `docs/api.md` (+28) — the principle and table pointer; CHANGELOG
  Unreleased with an honest Seats/restart line (holder process
  unchanged; per-call CLIs).

## Candidate

- Implementation commit `ecc96306` on `workflow/issue-309` (worktree
  `.kw/worktrees/issue-309`, base `4049e13b`). Implemented by the
  `grok/default` seat `grok-KPR-i309-routes`; reviewed and finalized
  by the Host.

## Evidence

- Host diff review (this run): enumeration test extracts codes from
  source; budgets kept (new reference; external skill +7 bytes);
  honest scoping note about #308's auto-reap.
- `./scripts/render-skills.py --check` — PASS.
- Affected suites, all exit 0: `test-issue-309-recovery-routes.py`
  (new), `test-progressive-disclosure.py`, `test-issue-271-dispatch-help.py`,
  `test-issue-299-delegator-webhook.py`, `test-issue-255-lifecycle-state.py`,
  `test-issue-49-grok-bot-host.py` (logs `/tmp/kpr-i309-*.log`). The
  `test-issue-308-resume-reconcile.py` suite does not exist on this
  branch's base (pre-#308) and runs on the integrated tree after the
  sink rebase.
- `.cache/final-validation.md`: verdict `pass`, candidate hash
  `acffd5d99fc7618f…`.
- Worker seat exact-stopped after acceptance (`state: stopped`).

## Known failures / unverified scope

- The sink rebases onto the #308/#310-advanced main; broker/CLI
  refusal-text conflicts are composed (keep #308's auto-reap semantics
  and #309's route stamps), and the integrated tree runs both the 309
  and 308 suites. Full inventory follows as the run's final gate. No
  release or install in this run (owner approval required).

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- scripts/install-local.sh
- scripts/kaola-acp.py
- scripts/kaola-dispatch.py
- scripts/kaola-grok-bot-verify.py
- scripts/kaola-launchd-broker.py
- scripts/kaola-locate.py
- scripts/kaola-recovery-routes.py
- scripts/kaola-tmux.sh
- scripts/render-skills.py
- scripts/validate.sh
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/claude-code-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/claude-code-kaola-project-runner/scripts/kaola-tmux.sh
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/codex-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/codex-kaola-project-runner/scripts/kaola-tmux.sh
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-tmux.sh
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/devin-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/devin-kaola-project-runner/scripts/kaola-tmux.sh
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/droid-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/droid-kaola-project-runner/scripts/kaola-tmux.sh
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/dsh-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/dsh-kaola-project-runner/scripts/kaola-tmux.sh
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/grok-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/grok-kaola-project-runner/scripts/kaola-tmux.sh
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-delegator/SKILL.md
- skills/kaola-delegator/references/handoff.md
- skills/kaola-delegator/references/host-restart.md
- skills/kaola-delegator/references/webhook-wake.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-tmux.sh
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/opencode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/opencode-kaola-project-runner/scripts/kaola-tmux.sh
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/zcode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/zcode-kaola-project-runner/scripts/kaola-tmux.sh
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/kaola-delegator/SKILL.md.tmpl
- templates/kaola-delegator/references/handoff.md.tmpl
- templates/kaola-delegator/references/host-restart.md
- templates/kaola-delegator/references/webhook-wake.md
- tests/contract/test-issue-309-recovery-routes.py
- tests/contract/test-progressive-disclosure.py

## Follow-Up Items

- kaola-project-manager mirror comment on KaolaBrother/kaola-project-manager#132 after
  merge (owner instruction: comment only).

## Final readiness

Ready: candidate reviewed, affected scope green, validation recorded.
Proceed to sink (merge) and archive.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-309/finalization-summary.md
