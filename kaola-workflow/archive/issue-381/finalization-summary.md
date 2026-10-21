# Finalization Summary — Issue #381

## Delivered

Implemented and fixed KPR #381 on `workflow/issue-381`: a view snapshot and
every holder turn publication share one dedicated leaf `view_lock`.

- Turn state, event cursor and projection turn row become visible as one unit
  at all five publication points: prompt response, synthetic (agent-initiated)
  finish, agent exit, prompt admission and synthetic start. `op_view` copies
  the projection, turn facts, cursor, state and a defensive
  `pending_permissions` snapshot under the lock and does no blocking I/O there.
- Leaf rule: no `self.lock`, `followers_lock`, condition wait, record write,
  fanout or wake while `view_lock` is held; `on_prompt_response` moves its
  fanout after the release.
- Review F1-F4 (6e7cc512): an admission whose frame was written while the agent
  exited publishes `process_exited` on that exit's cursor instead of reviving
  `active=true`; the synthetic finisher rechecks ownership under `view_lock`;
  Kimi provider evidence is read before the lock.
- Review R1 (50aa964b): the Codex `threadStatus` error writer's active check
  and write run under `view_lock`, and the synthetic finisher decides its
  outcome from the error current under that lock, reusing the pre-read summary
  only when the evidence is unchanged and otherwise publishing `evidence-raced`
  (the response branch's rule). Provider I/O stays outside the lock.
- `docs/api.md` (restart boundary, started-turn end-event rule),
  `CHANGELOG.md` (Seats: restart required), `scripts/validate.sh` and the 11
  generated holder copies are updated.

Candidate: `50aa964b988a9b602df8c4be35de3fc636dcde3b` on `workflow/issue-381`;
commits `78ccb5c1` + `6e7cc512` + `50aa964b` over base `2dfc679e`. No tag,
release, publish, install, or KPM-side operation was performed.

## Acceptance Evidence

- Host acceptance of `50aa964b`: independent review of the R1 diff, Host-run
  `render-skills.py --check` PASS, 4 suites exit 0, review clean-env harness
  19/19 interleavings and 7/7 boundary probes OK.
- Independent review and recheck: `/tmp/kpr381rev/REVIEW.md`,
  `/tmp/kpr381rev/recheck-6e7cc512/RECHECK.md` (F1-F4 confirmed fixed; R1 raised).
- R1 author evidence: `/tmp/kpr381-r1/` (`validate.log` 7 suites exit 0 with
  381 = 18 PASS; `extra-2.log`, `extra-all.log`, `boundary-probes.log`;
  mutation proofs `mut-M1.diff`/`.log` kill cases 16-18, `mut-M2.diff`/`.log`
  kill case 18; `render.log`).
- Finalization validation on the candidate: `/tmp/kpr381-final/validate.log`.

## Known Failures and Unverified Scope

- No full-inventory `validate.sh` run; the focused and adjacent suites cover
  the changed holder paths.
- No live external platform UAT; the contract suites use a stub ACP agent.
- Non-blocking review note: the `agent-exited-after-write` error code is
  returned on the admission receipt (`wait=False`); a default `wait=True` call
  returns the correct `process_exited`/`mutation_performed:true` turn receipt
  without that code (`/tmp/kpr381rev/recheck-6e7cc512/wait-admission-probe.log`).
- `scripts/kaola-acp-holder.py` is in the operator restart set, so a running
  holder keeps the old publication behavior until it restarts.

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
- tests/contract/test-issue-381-view-snapshot.py

## Follow-Up Items

- No new follow-up issue was filed by this run.
- Holder restart remains an operational note.
- No release, tag, publish, or install is part of this finalization.

Final readiness: ready. Merge sink to `main`, close #381 with the
Host-supplied closing comment after publication is verified, archive under
`kaola-workflow/archive/issue-381/`, and remove the run worktree.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-381/.cache/final-validation.md
- kaola-workflow/archive/issue-381/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-381/finalization-summary.md
- kaola-workflow/archive/issue-381/mission-ledger.jsonl
- kaola-workflow/archive/issue-381/workflow-state.md
