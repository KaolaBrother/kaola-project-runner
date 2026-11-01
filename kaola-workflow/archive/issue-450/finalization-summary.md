# Issue #450 finalization summary

## Delivered

Candidate `4f75ba4b1a6e984379a25d80cfbca9fdf46fec3d`. Devin Sideagent starts refuse explicit or inherited resume/continue, use a seat-private `DEVIN_SESSIONS_DIR`, verify the `session/new` ID against pre-existing inventory and Runner seat records, and buffer then reject foreign session IDs instead of projecting their content. A later foreign stream fails the holder and stops the agent. Sideagent role cannot be retroactively assigned to an unverified session.

The Grok Bot pin-delta restriction now runs only at `--require-pinned`, the release boundary, while ordinary development rendering works after a release. Other pin checks stay in place; the verifier uses the same boundary and does not claim the release gate was run. This addresses the clean-baseline post-release #449 archive delta; release pin checking remains required. The operator diff includes `scripts/kaola-acp-holder.py`, so `CHANGELOG.md` records Seats: restart required.

## Acceptance and evidence

Host acceptance: PASS for candidate `4f75ba4b` in the current conversation, explicitly covering the four defense layers, DB isolation, renderer gate and tests, and the locally unproven Studio vector. Controlled `validate.sh --suite test-devin-regressions.py --suite test-issue-255-lifecycle-state.py --suite test-issue-49-grok-bot-host.py` passed 36/36, 178/178 and 45/45 on Python 3.13/Bash 5; `/tmp/kpr450-controlled-validation.log`. Render `--write` and `--check` passed; post-commit `--check` passed. The explicit release gate correctly refused the post-release delta.

Mechanism, sandbox observations and timing evidence: `docs/devin-sideagent-origin-450.md`. KPR record directories include platform and seat name plus a digest of the repository path; equal repository digests do not establish a shared record directory. Devin's native DB defaults to shared user storage, and `--continue` lists and loads the latest repository session; the new Sideagent path isolates that DB and refuses continuation. A two-session same-directory sandbox followed by Sideagent start produced a fresh third ID, but the unauthenticated earlier sessions did not persist. The Studio fresh-start-to-foreign-session vector remains unproven locally; these defenses stand without claiming reproduction.

Earlier #255 diagnostic runs had node timing failures. On Python 3.13, the recovery batch case timed out on both candidate and baseline `9ce17666` at different points; the checkpoint case passed individual reruns on both. The earlier build-skew case passed individual reruns on both. The final controlled full #255 suite passed, so no test exception was used. Root cause for the earlier timeouts remains unknown. Studio VRPAI Host was not touched.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/devin-sideagent-origin-450.md
- scripts/kaola-acp-holder.py
- scripts/kaola-acp.py
- scripts/kaola-grok-bot-verify.py
- scripts/render-skills.py
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/antigravity-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/hermes-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/hermes-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- tests/contract/test-devin-regressions.py
- tests/contract/test-issue-49-grok-bot-host.py

## Follow-Up Items

No new issue: the observed timing symptoms were searched using `repo:KaolaBrother/kaola-project-runner "255" timeout in:title,body` (1 hit, closed #405, holder timing family); the final controlled suite passed and no new cause was established. The unproven Studio path is explicitly accepted by Host with the defenses in place; no claim of local reproduction or universal fault freedom.

## Readiness

Host accepted the candidate; ready for merge sink, issue closure, and archive. No release or Studio Host restart is part of this run.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-450/.cache/final-validation.md
- kaola-workflow/archive/issue-450/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-450/finalization-summary.md
- kaola-workflow/archive/issue-450/mission-ledger.jsonl
- kaola-workflow/archive/issue-450/workflow-state.md
