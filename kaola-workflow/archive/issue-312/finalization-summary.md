# Finalization summary — issue-312

## Delivered

Fix for #312 plus the KT binding addendum (owner-relayed, comment
6144950913 on #312): live-seat issue drift is surfaced advisory, and the
name contract matches KT's six rules.

- `scripts/kaola-dispatch.py`: `project --seats` and the Delegator seat
  summary report advisory `issue_drift` when a live seat's CURRENT
  dispatch issue differs from the `i<ISSUE>` in its session name, or
  when that name-issue has no active run — the row suggests exact-stop
  at the next safe point and a fresh standard-named session. Nothing
  blocks, renames, or stops the seat; the holder is unchanged.
- `templates/orchestrator/references/issue-dispatch.md`: the explicit
  rule — new issue ⇒ new session; never retarget a live seat to another
  issue (exact-stop at a safe point, then a fresh standard name).
- KT alignment (`af1646d4`, per the six points): `-general-` names
  (`<platform>-<CODE>-general-<purpose>`) are accepted non-issue names
  (`name_role: general`, no `issue_name`); `<CODE>` must start with a
  letter; `no-active-run` now means NOT exactly one in-progress
  non-bundle run whose claim shares the session repo's git origin
  (archived and bundle runs never count); `issue_name` remains exactly
  the four closed values, additive, with the `kaola-acp-list/1` schema
  name and all existing fields unchanged; null `agent_alive` stays
  unknown-not-ended.
- The shared fixture grew to 27 rows (general-form rows included) with
  the join rule restated per the KT points; Kaola Terminal mirrors once
  this file publishes.
- Tests: `test-issue-312-seat-drift.py` (339 lines): live-seat drift is
  advisory and does not stop; pure drift rules; execute copies the issue
  and does not refuse or stop; the rendered reference states the
  new-session rule; docs/inventory registration. The 313 suite extended
  for the grammar/role changes. Docs: `docs/api.md`, `docs/conventions.md`,
  `docs/issue-dispatch-display.md`; CHANGELOG Unreleased (per-call CLI;
  no seat restart).

## Candidate

- Commits `1e149990` (drift advisory + template rule) and `af1646d4`
  (KT six-point alignment) on `workflow/issue-312` (worktree
  `.kw/worktrees/issue-312`, base `46fb575d`). Implemented by the
  `grok/default` seat `grok-KPR-i312-drift`; reviewed and finalized by
  the Host.

## Evidence

- Host diff review (this run, two passes): advisory-only proven at both
  layers; each KT point verified against the code (general form,
  grammar, exactly-one non-bundle same-origin rule, additive schema,
  untouched null semantics).
- `./scripts/render-skills.py --check` — PASS.
- Affected suites, all exit 0: `test-issue-312-seat-drift.py` (new),
  `test-issue-313-name-advisory.py` (updated),
  `test-issue-271-dispatch-help.py`, `test-issue-273-list-identity.py`,
  `test-issue-295-delegator-seats.py`, `test-progressive-disclosure.py`,
  `test-issue-244-dispatch.py` (logs `/tmp/kpr-i312-*.log`).
- `.cache/final-validation.md`: verdict `pass`, candidate hash
  `8c0181b1e8425cc1…`.
- Worker seat exact-stopped after acceptance (`state: stopped`).

## Known failures / unverified scope

- No release (owner releases #308-#313 together). Kaola Terminal's
  mirror test happens on its side once the fixture publishes.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- docs/conventions.md
- docs/issue-dispatch-display.md
- scripts/kaola-acp.py
- scripts/kaola-dispatch.py
- scripts/kaola-session-names.py
- scripts/render-skills.py
- scripts/validate.sh
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-session-names.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-session-names.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-session-names.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-session-names.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-session-names.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-session-names.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-session-names.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/issue-dispatch.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kaola-project-runner/scripts/kaola-session-names.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-session-names.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-session-names.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-session-names.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/references/issue-dispatch.md
- tests/contract/kaola-terminal-name-contract.json
- tests/contract/test-issue-312-seat-drift.py
- tests/contract/test-issue-313-name-advisory.py
- tests/contract/test-progressive-disclosure.py

## Follow-Up Items

- None.

## Final readiness

Ready: candidate reviewed, affected scope green, validation recorded.
Proceed to sink (merge) and archive.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-312/finalization-summary.md
