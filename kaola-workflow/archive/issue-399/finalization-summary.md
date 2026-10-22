# Finalization Summary — Issue #399

## Delivered

Fixed #399 on `workflow/issue-399`: a Host `state.decisions` row is attention
only while it is open, and a Delegator-source turn end consumes the attention
it read without re-waking the same batch.

`scripts/kaola-record-contract.py` `host_view()` no longer projects an
`owner: host` decision with `status: settled` as a `host-decision` attention
row. A settled row that still carries `transcribed` keeps its
`transcribed-check` row for the pending-adoption migration shape, and a
pending Host decision still produces exactly one `host-decision` row. This
matches the holder's `open_registered_decision_rows` rule.

`scripts/kaola-acp-holder.py` uses a separate
`delegator_turn_attention_seen` mark for a `prompt_source: delegator` turn
end (send or steer). `_delegator_pending_facts` treats either that mark or
the Host-delivered `host_attention_seen` mark as already consumed, so the
same rows no longer wake `question_waiting` at every Delegator turn end.
`host_attention_seen` stays the Host-delivered mark read by the Sideagent
node settle and relay checks; a node-written attention the Host has not
received still reaches the Host (`host_owned`, not `node_quiet`). The pure
`delegator_turn_wake_reason` contract is unchanged, as are self turns,
including #315's compaction-reload registered decision.

The run adds `tests/contract/test-issue-399-question-attention.py` (19 tests:
settled/pending/transcribed projections, projected body, the Delegator mark,
a changed fingerprint still waking once, the unknown-body boundary, the
node-settle order and Host-delivered control, the deferred all-idle flush
second read, and the #315/#324 self-turn cases) and registers it beside
`test-issue-324-wake-fixes.py` in both `scripts/validate.sh` inventories.
`CHANGELOG.md` gains an `Unreleased` section with `Fixes #399` and
`Seats: restart required`; both changed scripts are in the operator restart
set and this change does not install. `docs/api.md` states both rules in its
wake table, its undelivered-attention paragraph, the `question_waiting`
paragraph, and the node path's separate-mark wording. The 11 generated worker
Skill copies of the holder and the orchestrator record-contract copy were
re-rendered from source.

The branch also carries the standard post-release content-cycle unpin of the
four Grok Bot pin paths (`templates/grok-bot/accepted-revision.json` plus the
three `hosts/grok-bot/` products), a release-cycle state change rather than
issue behavior. No #400 file, worktree or branch was touched.

Candidate: `60a933f9` on `workflow/issue-399`, the merge of `2a070611`
(base `b57eca17`, v0.9.24 pin) with main `17fd5121` (which carries #400).
Host acceptance: independent review 7/7 PASS and delta re-review PASS; the
blocking node-wake finding is resolved by the separate mark and verified by
the two-way probe, and all four Low findings are fixed.

## Evidence

- Pre-fix counter-proof: the 19-test suite run against the unfixed v0.9.24
  tree has 11 failures/errors (settled projection, mixed/projected body,
  Delegator consumption, new attention, unknown body, and the node-settle
  order).
- Post-fix suite: 19/19 PASS in 5.0 s.
- Node probe `/tmp/kpr399-node-probe-fixed.py`, driven through the real
  `_delegator_turn_end_reason`: pre-turn `host_owned=True`; after the
  Delegator turn (`host=F0`, `delegator=F1`) `host_owned=True` and not
  `node_quiet`; after a self-carrier delivery (`host=F1`) `node_quiet=True`.
  The same probe on merge-rehearsal tree `56a69448` gives the same results.
- Merge rehearsals: reviewer-side `d0008483` and this side `56a69448`; the
  only conflict was `CHANGELOG.md` (two `## Unreleased` sections). The actual
  integration merge `60a933f9` keeps one `## Unreleased` header, both `Fixes`
  lines (#399 and #400), one `Seats: restart required` and both bullets; the
  holder auto-merged with #400 and no #400 file was edited.
- Final focused validation, run from the merged candidate tree at `60a933f9`,
  exit 0:
  `./scripts/validate.sh --suite test-issue-302-delegator-wake-gate.py --suite test-issue-315-decision-wake.py --suite test-issue-324-wake-fixes.py --suite test-issue-341-agent-initiated-turn.py --suite test-issue-392-host-turn-done-wake.py --suite test-issue-399-question-attention.py --suite test-issue-255-lifecycle-state.py --suite test-issue-259-record-contract.py --suite test-issue-349-checkpoint-verb.py --suite test-issue-400-placeholder-lifecycle.py`
  - 302 39/39; 392 8/8; 315 6/6; 324 10/10; 399 19/19; 341 9/9;
    255 171/171; 259 63/63; 349 39/39; 400 4/4.
  - `render-skills.py --check` PASS (budgets OK); `grok-bot-verify` PASS at
    the content stage.
  - Log: `/tmp/r399-final-merged-validation.log`; render log
    `/tmp/r399-final-render-pre.log`.
- Validation record:
  `kaola-workflow/issue-399/.cache/final-validation.md`, validated candidate
  hash `8541481b3959b2b1ca5f99016e160da9f6e26a53ca72c58aa8117612769df16d`,
  command: `./scripts/validate.sh --suite test-issue-302-delegator-wake-gate.py --suite test-issue-315-decision-wake.py --suite test-issue-324-wake-fixes.py --suite test-issue-341-agent-initiated-turn.py --suite test-issue-392-host-turn-done-wake.py --suite test-issue-399-question-attention.py --suite test-issue-255-lifecycle-state.py --suite test-issue-259-record-contract.py --suite test-issue-349-checkpoint-verb.py --suite test-issue-400-placeholder-lifecycle.py`.

## Known failures or unverified scope

- The focused run is a 9-suite subset, not whole-inventory coverage.
- No live external-platform UAT was run; the change is holder-side attention
  state and record-contract projection, exercised by the mock ACP holder and
  the existing #302/#315/#324/#341/#392 real-holder harnesses.
- Running holders and the record contract keep the old wake behavior until
  they restart; the `Unreleased` section states `Seats: restart required`.
  This change does not install.
- The content-cycle unpin leaves the Grok Bot bridge at the content stage
  (`saveable: false`); a later release pins the content commit. The
  `webhook-wake.md` reference is 8181 B, 11 B under its 8192 B budget, so no
  substantive sentence was added there.

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
- scripts/kaola-record-contract.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/antigravity-kaola-project-runner/scripts/kaola-record-contract.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-record-contract.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-record-contract.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-record-contract.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-record-contract.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-record-contract.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-record-contract.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/scripts/kaola-record-contract.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- tests/contract/test-issue-399-question-attention.py

## Follow-Up Items

- No new follow-up issue was filed by this run; the review's Low findings were
  fixed in this branch.
- No release, tag, publish, install, or KPM-side operation is part of this
  finalization.

Final readiness: ready. Merge sink to `main`, verify publication, close #399,
archive under `kaola-workflow/archive/issue-399/`, and clean up the run
worktree and branch.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-399/.cache/final-validation.md
- kaola-workflow/archive/issue-399/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-399/finalization-summary.md
- kaola-workflow/archive/issue-399/mission-ledger.jsonl
- kaola-workflow/archive/issue-399/workflow-state.md
