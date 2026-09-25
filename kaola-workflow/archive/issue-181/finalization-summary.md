# Finalization summary - issue-181

Issue: #181 - record the effective permission mode at start; argparse None defaults; slim drain-restart
Branch: workflow/issue-181
Candidate: fd29aebb7c2a814b580eee1e2d17b42f01026d1d (base main 1e10f0d, no rebase needed)
Sink: merge
Acceptance: Claude Code review, receipt `claude-code-KPR-i181-review-3` - **VERDICT: PASS**
(after three rounds: initial FAIL on two blockers, repair PASS, delta re-review PASS)

## Delivered

1. **One default-fill site.** `command_start` resolves the effective permission mode
   (`--mode`, else the platform `ACP_SKIP_MODE` default) once and uses it for both the holder's
   recorded `start_selection` and the ACP config option. A fresh `start` without `--mode` records
   what it applied: claude-code `bypassPermissions`, droid `auto-high`; a platform with no default
   (dsh, cursor-cli, opencode) still records `null`.
2. **The two duplicate default sites removed.** The second fill site #163 added to
   `apply_recorded_selection` is gone, and so is the third copy of the same table in
   `kaola-tmux.sh`, machine-verified to have been an exact duplicate of `ACP_SKIP_MODE`. That layer
   now forwards only an explicit `--permission-mode`.
3. **`sys.argv` re-read replaced by argparse `None` defaults.** `_selection_explicit` reads
   `None`-ness, so prefix abbreviations and the `--flag=value` form count as explicit where the old
   scan missed them. `--fast` defaults to `None`, and a `fast_intent()` normalizer keeps every
   consumer and receipt reporting `off` for an absent flag.
4. **`drain-restart` slimmed.** The 0.2 s idle poll is gone: a live holder gets one idle read
   followed by its already-atomic `require_idle` stop, a busy seat gets an immediate
   `drain-not-idle` refusal, and retry timing stays with the Agent. A seat whose holder is already
   gone restarts without an idle read. The post-`start` `command_list` scan is gone; `adoption` is a
   direct read of the new start's own `dispatcher`.
5. **LOW leftovers.** Locator `--intent` narrowed to the values that were ever read (`start`,
   `resume`); the three `KAOLA_ACCEPTED_REVISION` env scrubs and both constants removed, since
   nothing in the repository ever set that variable (the revision travels as holder argv).

## Files Changed

14 non-generated paths plus 51 generated copies.

- Production source: `scripts/kaola-acp.py`, `scripts/kaola-acp-holder.py`, `scripts/kaola-locate.py`,
  `scripts/kaola-tmux.sh`
- Templates: `templates/references/acp.md.tmpl`,
  `templates/orchestrator/references/zcode-host-dispatch.md.tmpl`
- Docs: `CHANGELOG.md`, `docs/api.md`, `docs/zcode-host.md`
- Tests: `test-issue-162-upgrade-safety.py`, `test-issue-22-bypass-all-approvals.py`,
  `test-issue-24-opencode-no-skip-all.py`, `test-issue-51-runner-integration.py`,
  `test-devin-regressions.py`
- Generated: `skills/**`, `hosts/**` (render output, never hand-edited)

Production source (scripts/ + templates/) is **net -9** across 1e10f0d..fd29aeb
(-23 excluding comments and blank lines).

## Test Coverage

- New/updated: `test_start_records_the_effective_mode_not_the_raw_flag`,
  `test_drain_restart_keeps_an_abbreviated_command_and_explicit_mode` (verified FAILING on baseline
  1e10f0d and on 80ecfb2, passing here), `test_drain_restart_revives_a_cleanly_stopped_seat`
  (verified FAILING on 80ecfb2), plus the two legacy-seat mode tests re-pointed at the effective
  value and the shell-table assertions in the #22/#24/#51/devin suites moved to the single
  remaining site.
- Regression custody kept green: the #122/#132 pre-spawn refusal rows and the #180 call-count
  counter in `test-issue-164-pre-spawn-bridge-facts.py` (7/7).

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- docs/zcode-host.md
- scripts/kaola-acp-holder.py
- scripts/kaola-acp.py
- scripts/kaola-locate.py
- scripts/kaola-tmux.sh
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
- templates/orchestrator/references/zcode-host-dispatch.md.tmpl
- templates/references/acp.md.tmpl
- tests/contract/test-devin-regressions.py
- tests/contract/test-issue-162-upgrade-safety.py
- tests/contract/test-issue-22-bypass-all-approvals.py
- tests/contract/test-issue-24-opencode-no-skip-all.py
- tests/contract/test-issue-51-runner-integration.py

## Documentation Docking

DOCKED. `.cache/doc-docking.md` records every checked surface. `CHANGELOG.md` carries the #181
entry with `Seats: restart required.`; `docs/api.md` and `docs/zcode-host.md` describe the slimmed
drain-restart and the stopped-seat restart; both reference templates were updated and the generated
copies regenerated byte-identical. No new operator variable; no public API shape change.

## Follow-Up Items

None. This run discovered no defect outside its own scope, so no follow-up issue was filed and no
`filed: #N` line applies. The issue body's own deferrals (#179's `seat_freshness` parameters and the
`kaola-quota.py` restart-set question) were placed in S2 by the issue author and are not this run's.

## Status

Ready for the sink. Every mission is done, acceptance is granted, documentation is docked, and
validation is green on the frozen candidate.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-181/.cache/doc-docking.md
- kaola-workflow/archive/issue-181/.cache/final-validation.md
- kaola-workflow/archive/issue-181/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-181/finalization-summary.md
- kaola-workflow/archive/issue-181/mission-ledger.jsonl
- kaola-workflow/archive/issue-181/workflow-state.md
