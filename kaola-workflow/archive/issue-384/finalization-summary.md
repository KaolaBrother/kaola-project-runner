# Finalization Summary — Issue #384

## Delivered

Implemented and repaired KPR #384 on `workflow/issue-384`: `view` still returns
the compacted snapshot, but now discloses what that snapshot cannot carry.

- `messages_dropped` counts message rows removed from `messages[]` by the
  timeline and byte caps.
- `earliest_cursor` is the first cursor in the returned `messages[]`, and
  `null` when the array is empty.
- `truncation.rows.messages` separates `timeline` (`timeline-cap`) and `bytes`
  (`view-bytes`) drops from `restart` (`holder-restart`), whose
  `boundary_cursor` records the restored historical cursor and whose `dropped`
  is `null` only when a positive historical boundary exists.
- `truncation.rows` also counts dropped tool cards, turns and answered
  permissions; `truncation.event_log` records the event-log gap, its reason and
  the oldest retained event cursor.
- `cursor_gap` now covers both an event-log gap and missing projection rows.
  Every class that actually lost rows contributes its oldest surviving
  boundary to the gap floor: message cursors, turn `start_cursor`, answered
  permission `cursor`, and an internal first-seen cursor for tool cards. A
  class with no loss contributes nothing, so historical loss does not report a
  gap for every later `--since`.
- `truncated_event_log` and `truncated_rows` split the two new classes. The
  legacy `truncated` boolean remains the union of all previous cap signals,
  including thinking-tail and per-tool content clipping, plus the two classes;
  it is not their OR.
- Review R1 was fixed in `cff5caa3`; review R2/R3 narrowed the docs to the
  actual restart evidence limit (some agent-initiated turns do record
  `turn_started`) and to the remaining content-cap class.
- `docs/api.md`, `docs/acp-watch/list-view.md`, the frozen view sample,
  `CHANGELOG.md`, `scripts/validate.sh` and the 11 generated holder copies are
  updated.

Candidate: `cff5caa336639302152d57c4d5a59b6cb3da4684` on
`workflow/issue-384`; implementation `22c59dbd`, review repair `cff5caa3`,
over base `159557652cddc8dae472818fd85cdee570ceb0f6`. No tag, release,
publish, install, or KPM-side operation was performed.

## Acceptance Evidence

- Host acceptance of `cff5caa3`: R1-R3 repair independently confirmed; the
  three non-message-row probes pass; review's full 10/10 probes pass; render
  check and focused/adjacent suites exit 0.
- Independent review: `/tmp/kpr384rev/REVIEW.md`; R1 probes re-run in a clean
  environment at `/tmp/kpr384rev/probes-r1-final.log` (3/3 OK), full probes at
  `/tmp/kpr384rev/probes-all-fixed.log` (10/10 OK).
- Focused and adjacent validation on clean tip `cff5caa3`, exit 0:
  `test-issue-384-view-disclosure.py` 9/9, `test-acp-watch-contract.py` 20/20,
  `test-acp-follow-contract.py` 12/12, `test-issue-381-view-snapshot.py` 18/18,
  `test-acp-contract.py` 87/87, `test-generated-skills.py` PASS,
  `test-issue-380-client-message-id.py` 20/20; `render-skills.py --check`
  PASS. Log: `/tmp/kpr384-r2-final-validate-clean.log`.
- Validation record: `kaola-workflow/issue-384/.cache/final-validation.md`
  (candidate hash `49aa5d02a9822f976f316d7ea7d416a9b1b93748c278ca3c76b3dac142efbf08`).
- Pre-fix counter-proof: `/tmp/kpr384-prefix/prefix-run.log` (new suite fails
  6/6 against the pre-fix holder).

## Known Failures and Unverified Scope

- No full-inventory `validate.sh` run; the focused and adjacent suites cover
  the changed holder, view, follow, dispatch and generated-skill paths.
- No live external platform UAT; the contract suites use mock ACP agents.
- `scripts/kaola-acp-holder.py` is in the operator restart set, so a running
  holder keeps the old view disclosure until it restarts.
- The restart row count remains unknowable by design; the null is recorded as
  unknown, not zero, and no replay is claimed.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/acp-watch/list-view.md
- docs/api.md
- scripts/kaola-acp-holder.py
- scripts/validate.sh
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
- tests/contract/fixtures/kaola-acp-view-1.sample.json
- tests/contract/test-issue-384-view-disclosure.py

## Follow-Up Items

- No new follow-up issue was filed by this run.
- Holder restart remains an operational note.
- No release, tag, publish, install, or KPM-side operation is part of this
  finalization.

Final readiness: ready. Merge sink to `main`, close #384 with the Host-supplied
closing comment after publication is verified, archive under
`kaola-workflow/archive/issue-384/`, and remove the run worktree.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-384/.cache/final-validation.md
- kaola-workflow/archive/issue-384/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-384/finalization-summary.md
- kaola-workflow/archive/issue-384/mission-ledger.jsonl
- kaola-workflow/archive/issue-384/workflow-state.md
