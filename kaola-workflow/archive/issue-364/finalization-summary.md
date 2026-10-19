# Finalization Summary — issue-364

## Delivered

`scripts/kaola-recovery-routes.py` gained one `route` row for each of the seven
audited codes the recovery-route audit reported missing: `checked-out`,
`done-not-retired`, `entry-needs-one-verb`, `live-session`,
`returned-unreadable`, `state-bloat`, `unmerged-or-unpushed`. Each row names an
executable next step consistent with the emitting code (`kaola-dispatch.py`
sweep W1/B1 keep/skip reasons, `state check` diagnosis, and node checkpoint
entry validation) and with the existing table style. `sideagent-default-unbound`
was already routed and untouched. Table, generated skill copies, and the
changelog only; no behavior change.

## Candidate

Branch `workflow/issue-364`, two commits on the release merge 72488b3c:

- `f37a1b54` chore(release): open post-v0.9.21 content cycle — restores the four
  pin-delta paths to content stage per the a6af2d88/bca682af convention so the
  render gate can verify a development change on a pinned release tree.
- `70602fdf` Route the seven audited recovery codes still missing rows (#364):
  `scripts/kaola-recovery-routes.py` + regenerated `skills/` copies +
  `CHANGELOG.md` Unreleased entry.

## Evidence

- Reproduction on baseline 72488b3c: `python3
  tests/contract/test-issue-309-recovery-routes.py` → `Ran 8 tests`,
  `FAILED (failures=1)`, missing list = the seven issue-named codes.
- Post-fix in this worktree: same command → `Ran 8 tests`, `OK`.
- `./scripts/validate.sh --suite test-issue-309-recovery-routes.py` → all lanes
  PASS (suite OK, render-skills PASS, 13 validate-skill PASS,
  grok-bot-verify PASS), exit 0.
- `./scripts/render-skills.py --check` → PASS (content stage, budgets OK).
- Recorded receipt: `kaola-workflow/issue-364/.cache/final-validation.md`
  (verdict pass, validated_candidate_hash b60460c9678d…).
- Host acceptance: user re-ran the suite (8/8 OK) and `render-skills --check`
  (exit 0) in this worktree, and re-confirmed the baseline failure on main
  72488b3c.

## Known failures or unverified scope

- The 133-suite full inventory was not run on this candidate; per AGENTS.md the
  focused suite plus render check was the agreed scope, and the Host runs the
  full inventory at its own boundary.
- The `f37a1b54` content-cycle commit returns the bridge to unpinned content
  stage; the pin returns at the next release commit, as usual.

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
- scripts/kaola-recovery-routes.py
- skills/antigravity-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/grok-bot/accepted-revision.json

## Follow-Up Items

None filed: the run discovered no new defect. The issue body needed no
correction — its measured list and hypothesis matched the observed extraction.

## Readiness

Ready for merge-sink close-out. `Seats: restart not required` — the diff does
not touch the operator restart set (`scripts/kaola-acp-holder.py`,
`kaola-zcode-acp.py`, `kaola-quota.py`, `kaola-record-contract.py`,
`kaola-acp-paths.py`, `scripts/adapters`, `platforms`).

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-364/.cache/final-validation.md
- kaola-workflow/archive/issue-364/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-364/finalization-summary.md
- kaola-workflow/archive/issue-364/mission-ledger.jsonl
- kaola-workflow/archive/issue-364/workflow-state.md
