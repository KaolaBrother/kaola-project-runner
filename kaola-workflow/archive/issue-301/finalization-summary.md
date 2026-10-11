# Finalization summary — issue-301

## Delivered

Fix for #301: three platform-profile changes shipped as one feature.

- `platforms/codex.yaml`: `luna_model_profile` is now exactly "Computer-use
  worker only: drives GUI/browser/desktop QA and verification with
  screenshots and verdicts; not for general implementation, debugging, or
  design."; `luna_model_class` stays Worker; model id and effort unchanged.
- `platforms/claude-code.yaml`: `sonnet_model_profile` is now exactly
  "All-round execution worker, especially UI and 3D visual implementation.";
  class stays Elite, effort stays high.
- New tier `haiku` in `named_tiers` (`opus-xhigh,fable,sonnet,haiku`):
  name Claude Haiku, id `haiku`, class Worker,
  `haiku_model_profile` = "Fast all-round execution worker, well suited to
  well-scoped work, especially UI and 3D visual implementation." (Sonnet's
  previous profile with "Fast" added — owner amendment, Yanlei 2026-10-11
  14:31, reflected in the issue body), `effort=high` per Host-verified
  evidence (claude 2.1.295 help: `--effort` session-level, not model-gated;
  live probe `claude --model haiku --effort high` replied ok, 2026-10-11).
  `model_package_rule` already mapped haiku to subscription (verified).
- Registration sweep: `scripts/adapters/claude-code.sh` tier list, rendered
  skills (all ten + orchestrator + delegator references), README region,
  worker-profiles/host-platforms references through their templates, docs.
- Tests: `test-issue-218-preset-ids.py` extended — haiku preset row (class
  Worker, name, parameters, profile verbatim), pool membership (six Worker
  presets, haiku first), resolution in `project --seats` and the delegator
  view.
- CHANGELOG Unreleased entry with the verbatim texts and the effort
  evidence. Restart judgment (Host-corrected in `5820ef90`): per-call
  catalog reads see the new presets without restart, but the holder pins
  `platform.yaml` and the adapter mirrors the tier list — both in the
  operator test's restart set — so the section says **Seats: restart
  required** with drain-restart as the post-install refresh for running
  codex/claude-code seats.

## Candidate

- Commits `5777ff72` (implementation, grok seat `grok-KPR-i301-profiles`)
  and `5820ef90` (Host restart-note correction) on `workflow/issue-301`
  (worktree `.kw/worktrees/issue-301`, base `f5941744`). Reviewed and
  finalized by the Host.

## Evidence

- Host diff review: verbatim text match against the amended issue body for
  all three profiles; effort decision backed by the recorded probe; tier
  registration verified across manifest, adapter, rendered output,
  references and tests. One review finding (restart note) fixed on-branch.
- `./scripts/render-skills.py --check` — PASS.
- Affected suites, all exit 0: `test-issue-218-preset-ids.py` (extended),
  `test-issue-244-dispatch.py`, `test-issue-271-dispatch-help.py`,
  `test-issue-294-expert-ceiling.py`, `test-issue-295-delegator-seats.py`,
  `test-issue-296-shared-tier-seats.py`, `test-progressive-disclosure.py`,
  `test-issue-130-pty-retired.py` (logs `/tmp/kpr-i301-*.log`).
- `.cache/final-validation.md`: verdict `pass`, candidate hash
  `5a43777fe6fc64ee…`.
- Worker seat exact-stopped after acceptance (`state: stopped`).

## Known failures / unverified scope

- The full inventory runs before the release content commit, per the owner
  order. Release v0.9.6 follows this merge.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- README.md
- docs/api.md
- docs/architecture.md
- docs/zcode-host.md
- platforms/claude-code.yaml
- platforms/codex.yaml
- scripts/adapters/claude-code.sh
- skills/claude-code-kaola-project-runner/SKILL.md
- skills/claude-code-kaola-project-runner/references/platform.md
- skills/claude-code-kaola-project-runner/scripts/adapters/claude-code.sh
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/platform.yaml
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/platform.yaml
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-delegator/references/host-platforms.md
- skills/kaola-project-runner/references/profile-catalog.md
- skills/kaola-project-runner/references/worker-profiles.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/kaola-delegator/references/host-platforms.md.tmpl
- templates/orchestrator/references/worker-profiles.md.tmpl
- tests/contract/test-issue-218-preset-ids.py

## Follow-Up Items

- None.

## Final readiness

Ready: candidate reviewed, affected scope green, validation recorded.
Proceed to sink (merge) and archive.
