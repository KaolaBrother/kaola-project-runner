# Finalization Summary — Issue #255

## Delivered

Accepted candidate: 86d19f69982858879a51bf4afe4dfff06de1da1f (branch workflow/issue-255,
integrating the already-published #256 at a51b35ff). Agreed lifecycle state maintenance,
continuity and migration: the `kaola-dispatch.py state` tool (init/update/retire/view/check/
timer/migrate), one dispatch index with original locators and mirrored acceptance, `execute`
dispatcher/notify/held-seat admission, Host carrier with fresh per-batch Sideagent nodes, holder
feature checks and preserve-dispatched-workers stop, orchestrator/Delegator guidance and
references, conventions/design/API docs and CHANGELOG Unreleased (`Seats: restart required`).
The final N1 repair makes an item's own verified, unprompted live seat its count, and routes
planned dispatch of every scope through `execute`.

Joint final acceptance is PASS for this exact candidate and the scoped mandate:
- Host: /tmp/kpr-lifecycle-implementation-20261004/host-final-acceptance-86d19f69.md
  (issue comment 5985453785).
- Outer personal review: /tmp/kpr-lifecycle-implementation-20261004/outer-final-review-86d19f69.md
- Claude Code Opus Extra High: /tmp/kpr-lifecycle-implementation-20261004/opus-n1-final-review-86d19f69.md

Evidence reused because it matches the candidate bytes (no repeated QA):
- validate.sh on the committed tree: n1-dispatch-repair/validate15.log, exit 0, sha256
  996fa738c502d36005700944f3858b207977b07688f0f4e6d70d9512d774da96 (74 dispatch, 105 lifecycle
  tests; render --check PASS, budgets OK).
- Old-code proof: n1-dispatch-repair/old-1052f604-held-seat.log (three new tests fail on 1052f604).
- Native qa6 (model-driven Codex Host, one execute, collect, mirrored acceptance, exact cleanup)
  and qa6b (two pre-started seats admitted, third refused `count`): n1-dispatch-repair/qa6 and
  qa6b, SHA256SUMS 48 and 22 entries, all verified by both reviewers.
- Earlier native continuity, OpenCode and qa4/qa5 node evidence stays valid where holder,
  launcher and wrapper bytes are unchanged (holder ffe071dc…, kaola-acp.py 4b390e30…,
  kaola-tmux.sh c72a38a1…); consolidated-native-qa/ and final-review-repair-delivery.md.
All paths above are under /tmp/kpr-lifecycle-implementation-20261004/.

## Seven owner requirements (accepted answers against 86d19f69)

1. Template fidelity — met with limits. `state timer` compares native timer text with the
   canonical template; cadence stays in the Delegator file; the Host heartbeat is the skeleton
   plus the generated view written only by `state`; unavailable native readback is reported
   unverified. The replaced dispatch wording is pinned by a test. Limits: native timer readback
   per outer platform is unverified; no timer was created; the current outer hourly entry stays
   the installed version.
2. Current, nonredundant information — met with limits. Keyed records and revisions, bounded
   projections, retirement to capped tombstones, source-only node writes, one node batch per
   Host turn, one dispatch index. qa6: the index holds holders, receipts, locators, output kind
   and mirrored acceptance; host revision 14, handled = acked = 14, empty attention. Limits: two
   short runs of one task shape; qa6's accepted tasks stayed `done` and were not retired (see
   Known Findings); qa6 task links were Host-written after a refused task write.
3. Host autonomy and Sideagent lifecycle — met with limits. qa6 trace: reference reads,
   `--help` discovery, Host-authored assignments, one `execute` that started and sent both
   seats, `collect`, full originals read and checked by the Host, dispositions recorded, exact
   stops by holder; fresh nodes per batch with pointer-only writes and no session control; no
   compulsory Sideagent round trip. qa6b proves pre-started seat admission. Limits: Codex only
   for the model-driven pairing; fan-out of two; model-driven Host with pre-started seats is
   tool-probe and unit evidence only; no native `scope: implementation` through `execute`.
4. Cadence-independent supervision — met with limits. One existing timer with an identical body
   at 30, 60, 120 and 240 minutes (unit test); ordinary returns wake the Host directly;
   node-raised attention reaches the Host at its next turn boundary (qa6: 68 s after settle).
   Limits: no live run at the four cadences; only the existing outer hourly timer is
   live-observed; relay and adoption at an inquiry rest on guidance and unit tests.
5. Recovery and informed autonomy — met with limits. Both dispatch orderings work natively; a
   refused attempt no longer blocks its own retry; unverified, prompted, foreign-repo,
   other-preset, holder-mismatch, race-to-prompted, over-count and over-cap stay refused (unit);
   qa6's malformed task evidence was refused visibly and corrected by the Host in the same turn.
   Limits: short checkpoint range unit-only; node mode on Codex and ZCode only; mid-start
   interruption leaves a `starting` record; ZCode Host default stop does not sweep workers;
   relay across holder death unproven; O1–O3 unexercised. Not universal coverage.
6. Learning from mistakes — met with limits. The repeated qa4/qa5 pre-start refusal led to a
   reviewed change that retired the obsolete guidance by replacement and removed the duplicate
   count restriction, with no added rule; the fresh qa6 Host did not repeat the step. Limits:
   one confirming run; no self-modification engine or cross-session memory, by design.
7. Future upgrade continuity — met with limits. Additive state and index fields, migration
   plan/write/idempotency, holder feature checks, old persistent-Sideagent retirement guidance,
   isolated byte-matching copy installs, restart-required declaration. Limits: no shared
   install and no migration of a real consuming project; older-holder paths are unit-only;
   installed runtime evidence is Codex and ZCode only.

## Corrections recorded at acceptance

- qa6 task links: the earlier delivery called the empty `task_links` a deliberate Host ordering
  choice. That was wrong. The Host first attempted the task writes in the same shell command as
  `execute --state`; the `a-sum` write was refused (exit 2) because `evidence` was an object, the
  shell continued to `execute`, which reported the missing task. The Host then rewrote both
  tasks with list evidence and later wrote the task `dispatch` links itself. Nothing was lost or
  replayed; automatic tool-side link repair was not exercised. Host posted this correction on the
  issue (comment 5985453785). Raw evidence is unchanged.
- qa6 done-not-retired is not automatic compaction proof. A read-only `state check` on a byte
  copy of the qa6 final state (sha256 e11b2cc5…, revision 21) reports `done-not-retired` for
  `a-sum` and `b-sum` (finalization/qa6-state-check.json). qa5 retirement is separate evidence.
- `capture-truncated` is bounded evidence that requires the original locator and full read, not
  a task failure; when present, `reply_chars` and `excerpt_truncated` describe the cut capture.
- Manifest counts: final-review-repair-delivery.md said qa4/qa5 SHA256SUMS had 49/48 lines; the
  actual counts are 50/49 (files unchanged).

## Known failures or unverified scope

No known failing check on the candidate. Carried non-blocking observations: O1 (wake decided at
settle), O2 (problem checked before superseded), O3 (node failure notices not restored after a
holder restart), O5 (`held_seat` accepts a preset written on a hand-built live row without the
status receipt; send still gated by fresh `not_started`), O6 (the task-link description,
corrected above), O7 (qa6 done tasks not retired). Minor 7 (duplicated historical CHANGELOG
block) stays with Host release preparation. qa6 vs qa5 elapsed time (432 s vs 501 s) is
illustrative only, not a performance claim.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- AGENTS.md
- CHANGELOG.md
- docs/README.md
- docs/api.md
- docs/conventions.md
- docs/designs/lifecycle-state-2026-10-04/design.md
- docs/designs/lifecycle-state-2026-10-04/index.html
- docs/designs/lifecycle-state-2026-10-04/research/README.md
- docs/designs/lifecycle-state-2026-10-04/research/checkpoint-state-host-verdict.md
- docs/designs/lifecycle-state-2026-10-04/research/checkpoint-state.md
- docs/designs/lifecycle-state-2026-10-04/research/ckptstate-retrieval-notes.md
- docs/designs/lifecycle-state-2026-10-04/research/durable-returns-host-verdict.md
- docs/designs/lifecycle-state-2026-10-04/research/durable-returns-sources.md
- docs/designs/lifecycle-state-2026-10-04/research/durable-returns.md
- docs/designs/lifecycle-state-2026-10-04/research/fanout-host-verdict.md
- docs/designs/lifecycle-state-2026-10-04/research/fanout-retrieval-notes.md
- docs/designs/lifecycle-state-2026-10-04/research/fanout.md
- docs/designs/lifecycle-state-2026-10-04/research/kpr255-reclaim-retrieval-20261004.md
- docs/designs/lifecycle-state-2026-10-04/research/lifecycle-closure-agreement.md
- docs/designs/lifecycle-state-2026-10-04/research/reclaim-host-verdict.md
- docs/designs/lifecycle-state-2026-10-04/research/reclaim.md
- docs/designs/lifecycle-state-2026-10-04/research/sideagent-nodes-agreement.md
- docs/designs/lifecycle-state-2026-10-04/research/sideagent-nodes-final-reconciliation.md
- docs/dispatch-collect.md
- docs/zcode-host.md
- scripts/kaola-acp-holder.py
- scripts/kaola-acp.py
- scripts/kaola-dispatch.py
- scripts/kaola-tmux.sh
- scripts/validate.sh
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
- skills/kaola-delegator/SKILL.md
- skills/kaola-delegator/references/inquiry-report.md
- skills/kaola-delegator/references/snapshot.md
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/dispatch-collect.md
- skills/kaola-project-runner/references/duty-reconcile.md
- skills/kaola-project-runner/references/heartbeat-skeleton.md
- skills/kaola-project-runner/references/host-startup.md
- skills/kaola-project-runner/references/issue-dispatch.md
- skills/kaola-project-runner/references/lifecycle-state.md
- skills/kaola-project-runner/references/sideagent-node.md
- skills/kaola-project-runner/references/workflow-worktree.md
- skills/kaola-project-runner/references/zcode-host-dispatch.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
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
- templates/kaola-delegator/SKILL.md.tmpl
- templates/kaola-delegator/references/inquiry-report.md
- templates/kaola-delegator/references/snapshot.md
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/dispatch-collect.md
- templates/orchestrator/references/duty-reconcile.md
- templates/orchestrator/references/heartbeat-skeleton.txt
- templates/orchestrator/references/host-startup.md.tmpl
- templates/orchestrator/references/issue-dispatch.md
- templates/orchestrator/references/lifecycle-state.md
- templates/orchestrator/references/sideagent-node.md
- templates/orchestrator/references/workflow-worktree.md
- templates/orchestrator/references/zcode-host-dispatch.md.tmpl
- templates/references/acp.md.tmpl
- tests/contract/test-issue-118-seat-cap.py
- tests/contract/test-issue-162-upgrade-safety.py
- tests/contract/test-issue-244-dispatch.py
- tests/contract/test-issue-255-lifecycle-state.py
- tests/contract/test-issue-74-kaola-delegator.py
- tests/contract/test-issue-92-permission-wake-recovery.py
- tests/contract/test-zcode-heartbeat-contract.py

## Follow-Up Items

No new independent defect requires a filed issue; O1–O3 and O5–O7 are recorded observations
inside this accepted scope. Host-owned next duties, not performed by this run: release
preparation (fix the flagged duplicate CHANGELOG history, platform pins including the Grok Bot
`saveable: true` pin, restart statement, tag and publication verification), seat restart per
`Seats: restart required`, retirement of completed records in the actual project's state, and
exact reclaim of this Droid seat. The hourly Delegator stays active until release and close-out
are verified. No installation, shared configuration or runtime change was made.

Final readiness: accepted candidate ready for the authorized merge sink, archive, verified issue
closure and scoped branch/worktree cleanup. Lifecycle transaction receipts own final truth.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-codex-160-live-2026-10-03.md
- docs/harness-acp-compat-2026-10-01.md
- docs/harness-acp-compat-2026-10-03.md
- docs/harness-acp-reverify-2026-10-01.md

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-255/.cache/final-validation.md
- kaola-workflow/archive/issue-255/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-255/finalization-summary.md
- kaola-workflow/archive/issue-255/mission-ledger.jsonl
- kaola-workflow/archive/issue-255/workflow-state.md
