# Finalization Summary — Issue #382

## Delivered

Implemented KPR #382 on `workflow/issue-382`: the view `thinking` projection is
now per turn instead of holder-lifetime.

- `ViewProjection._reset_thinking_locked()` clears exactly `thinking_chars`,
  `thinking_text` and `thinking_message_id`.
- The reset runs only in `add_user_from_prompt` (after this holder's
  `session/prompt` frame is written and the complete turn is published) and in
  `start_agent_turn` (the agent-initiated synthetic turn boundary). `end_turn`
  does not reset, so a completed, cancelled or failed turn stays readable until
  the next turn opens.
- All prompt-refusal paths keep the previous turn's thought because they return
  before the admission publication: busy turn, holder mismatch, client-id
  replay/conflict, stopping holder, no ACP session, and an unwritten frame.
- Steer follows the documented matrix: native busy steer writes into the
  running turn and opens no turn; an idle steer is never written; an after-turn
  steer resets at its follow-up prompt admission; `steer_interrupt` resets at
  the new prompt turn it admits after a confirmed cancel.
- `docs/api.md` gains `### Per-turn thinking projection (Issue #382)` with the
  boundary matrix in prose and the known late-chunk attribution limitation;
  `CHANGELOG.md` records the fix and the restart requirement.
- `ThinkingTurnResetTests` (4 cases) is ported into
  `tests/contract/test-acp-watch-contract.py`; the 11 generated worker holder
  copies are re-rendered byte-identically from the source.

Candidate: `3391bfdfc804229733c8cf6e5f92b796cadc829d` on
`workflow/issue-382`, over base `52e264e1`. No tag, release, publish, install,
or KPM-side operation was performed.

## Acceptance Evidence

- Host acceptance passed on `3391bfdf`; astra independent review passed
  (113/113, 12/12 probes, mutation capture, generated surfaces byte-identical).
- RED proof: the ported tests ran against the pre-fix holder loaded from the
  base commit and failed 4 test methods / 6 subtest failures; the same tests on
  the candidate are 4/4 OK.
- Final focused validation on the candidate, exit 0:
  `./scripts/validate.sh --suite test-acp-watch-contract
  --suite test-acp-follow-contract --suite test-issue-341-agent-initiated-turn
  --suite test-issue-381-view-snapshot` — watch 20/20 (16 existing + 4 new),
  follow 12/12, issue-341 9/9, issue-381 18/18; `render-skills.py --check`
  PASS with budgets OK.
- Broader affected suites passed on identical bytes: `test-acp-contract`
  87/87, `test-issue-65-steering` 27/27, `test-issue-379-receipt-mutation`
  19/19, `test-issue-380-client-message-id` 20/20.
- Validation record: `kaola-workflow/issue-382/.cache/final-validation.md`
  (candidate hash `a20c77b12c1fa9db0391aeb4ead636925bd9f8e8fb0f52903f3ba16c5290e6cb`).

## Known Failures and Unverified Scope

- No full-inventory `validate.sh` run; the focused and adjacent suites cover
  the changed holder, view, follow and steer paths.
- No live external platform UAT; the contract suites use a stub ACP agent.
- Known limitation, documented in `docs/api.md`: ACP `session/update` carries
  no turn id, so a late `agent_thought_chunk` from an ended or cancelled turn
  that arrives after the next turn has opened can paint that turn and restore
  its old `messageId`. The guarantee is reset at the turn boundary, not strict
  per-turn attribution; no holder-local scoping was added because the wire
  cannot distinguish the chunks.
- `scripts/kaola-acp-holder.py` is in the operator restart set, so a running
  holder keeps the old thinking lifetime until it restarts.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- scripts/kaola-acp-holder.py
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- tests/contract/test-acp-watch-contract.py

## Follow-Up Items

- No new follow-up issue was filed by this run.
- Holder restart remains an operational note.
- No release, tag, publish, install, or KPM-side operation is part of this
  finalization.

Final readiness: ready. Merge sink to `main`, close #382 with the Host-supplied
closing comment after publication is verified, archive under
`kaola-workflow/archive/issue-382/`, and remove the run worktree.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-382/.cache/final-validation.md
- kaola-workflow/archive/issue-382/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-382/finalization-summary.md
- kaola-workflow/archive/issue-382/mission-ledger.jsonl
- kaola-workflow/archive/issue-382/workflow-state.md
