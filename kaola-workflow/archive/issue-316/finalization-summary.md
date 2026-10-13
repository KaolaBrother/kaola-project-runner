# Finalization summary — issue-316

## Delivered

Fix for #316: a resumed Host session records its tier state honestly
and `model_verified` is set from real session evidence.

- `scripts/kaola-acp.py`:
  - Resume with `--tier` applies that preset like a fresh start. A
    resume with no tier, model, or effort keeps the saved native
    selection (the #8/#268 contract) and records
    `tier_reason: resume-without-tier` — an explicit fact instead of a
    silent null.
  - `status`/`observe` read the actual model from the recorded session
    update stream (the ACP projection the runner already holds), or
    from the Claude Code session JSONL tail when that stream carries
    none — skipping synthetic entries and rejecting path-shaped ids;
    the native session file beats the ACP id, a newer event wins, and
    a read transcript with no model reports unreadable honestly.
    `model_verified` and `actual_runtime_model_id` are set from that
    evidence, clearing `actual-model-evidence-not-yet-read`.
- Tests: `test-issue-316-resume-model-evidence.py` (10 cases, 554
  lines): preserve records null tier and a tier still applies; the
  alias is not the transcript id and a preserved resume is not
  comparable; the transcript tail skips synthetic and rejects a path
  id; a recorded update wins and a missing file stays unread; the
  native session file beats the ACP id and a newer event wins; a read
  transcript with no model is unreadable; resume with tier applies it
  and records no omission reason; resume without tier records the
  reason and preserves selection; a turn with a recorded runtime model
  verifies it; resume without tier reports the actual model as not
  comparable.
- `docs/api.md` (+63); CHANGELOG Unreleased — Seats: restart not
  required (per-call CLI; holder unchanged).

## Candidate

- Implementation commit `4fd4a44b` on `workflow/issue-316` (worktree
  `.kw/worktrees/issue-316`, base `fa03c005`). Implemented by the
  `grok/default` seat `grok-KPR-i316-resume-tier`; reviewed and
  finalized by the Host.

## Evidence

- Host diff review (this run): apply-or-record tier semantics per the
  issue; model evidence from sources the runner already holds or the
  platform's own transcript, with honest fallbacks; holder untouched.
- `./scripts/render-skills.py --check` — PASS.
- Affected suites, all exit 0: `test-issue-316-resume-model-evidence.py`
  (new), `test-issue-268-selection-continuity.py`,
  `test-issue-244-dispatch.py`, `test-issue-271-dispatch-help.py`,
  `test-issue-162-upgrade-safety.py`, `test-issue-255-lifecycle-state.py`
  (logs `/tmp/kpr-i316-*.log`).
- `.cache/final-validation.md`: verdict `pass`, candidate hash
  `fe3f14f09d4f5340…`.
- Worker seat exact-stopped after acceptance (`state: stopped`).

## Known failures / unverified scope

- #317 still in flight; full inventory after the last merge. No
  release (owner releases).

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- scripts/kaola-acp.py
- scripts/validate.sh
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- tests/contract/mock-acp-agent.py
- tests/contract/test-issue-316-resume-model-evidence.py

## Follow-Up Items

- None.

## Final readiness

Ready: candidate reviewed, affected scope green, validation recorded.
Proceed to sink (merge) and archive.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-316/finalization-summary.md
