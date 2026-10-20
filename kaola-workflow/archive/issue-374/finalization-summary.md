# Finalization Summary — issue-374

## Delivered

The KPR-side `worktree-guard` receipt consumed by Kaola-Workflow is frozen in
`docs/api.md`: the top-level fields (`schema`, `repo`, `path`, `result`,
`occupants`, `probe`, `route`), the occupant and session shapes, and the stable
exit codes `0` clear / `3` occupied or `cwd-unverifiable` / `2` refused. The
documentation also records that every verified `list --include-dead` row whose
repo is the repo or the target contributes its process tree and recorded tool
cwd, so a Host, a Sideagent and a seat are all occupants.

The new `tests/contract/test-issue-374-worktree-guard-contract.py` asserts the
exact field sets for clear, occupied, `cwd-unverifiable` and refused receipts,
covers Host/Sideagent/seat rows and a live process, and is registered in
`scripts/validate.sh` (inventory and lane B). A field rename now breaks KPR's
own gate before a consumer does.

Kaola-Workflow side: `KaolaBrother/Kaola-Workflow` PR #1117 calls
`kaola-dispatch.py worktree-guard --repo <root> --path <worktree>` before its
own `git worktree remove`, acts on the receipt with typed
`worktree_occupied` / `worktree_cwd_unverifiable` / `worktree_guard_unavailable`
refusals, keeps the old behavior when no locator is installed, and carries the
path in the Claude, Codex, GitLab and Gitea editions. The PR was merged as
`e8c49f6dc61226edfdb5d5c41866baaafa1d55bf` before the review gate closed; the
Delegator kept that pre-review merge as an accepted exception with no rollback
and no KW release/tag. The fable review (`devin-KPR-i373-expert-review`)
verdicted KPR #374 PASS and KW #373 PASS, with K1 as the one MEDIUM KW finding
to follow up (the sink dev-worktree cleanup at ~L3607 lacks the typed
`worktree_occupied` envelope), K2 as an owner design decision (not
implemented), and K3 as optional.

## Candidate

Branch `workflow/issue-374` at
`f95f25d7` (rebased from the original `83fd9837` onto current main
`085ddc51`, which contains the merged #377). The rebase resolved the
`CHANGELOG.md` Unreleased union (both #377 and #374 entries) and kept both
`test-issue-377-runner-fallback.py` and
`test-issue-374-worktree-guard-contract.py` in `scripts/validate.sh`.

Changed surface: `CHANGELOG.md`, `docs/api.md`, `scripts/validate.sh`, and the
new contract suite. No runtime script changed; the Grok Bot bridge was already
at the unpinned content stage on main and remains there.

## Evidence

- Fable review verdict from `devin-KPR-i373-expert-review`: KPR #374 PASS;
  KW K1 MEDIUM follow-up, K2 owner decision, K3 optional.
- Affected suites on the rebased candidate, exit 0:
  `test-issue-374-worktree-guard-contract.py`,
  `test-issue-377-runner-fallback.py`,
  `test-issue-264-validate-lane-integrity.py`,
  `test-issue-275-core-contracts.py`,
  `test-issue-369-worktree-guard.py`,
  `test-issue-369-cwd-vanished.py`,
  `test-issue-309-recovery-routes.py`,
  `test-issue-271-dispatch-help.py`.
  Logs: `/tmp/kpr-374-rebased-suites.log` and
  `/tmp/kpr-374-extra-suites.log`.
- `./scripts/render-skills.py --check`: PASS (budgets OK, content stage).
  `kaola-grok-bot-verify`: PASS.
- Final validation record: `kaola-workflow/issue-374/.cache/final-validation.md`
  binds the candidate tree to the exact affected-suite command, verdict
  `pass`.
- KW four-chain evidence from the #374 delivery: `npm test` exit 0 on
  claude/codex/gitlab/gitea at `5d423c0f`; the new KW suite passed 134
  assertions per edition. KW PR #1117 is merged at `e8c49f6d`.

## Known failures or unverified scope

- A full `./scripts/validate.sh` inventory on this candidate was attempted
  twice while unrelated worktrees ran their own full inventories. Only
  timing-sensitive suites failed (`test-issue-323-antigravity-acp.py`,
  `test-issue-341-agent-initiated-turn.py`,
  `test-issue-348-backstop-sweep.py`, `test-acp-contract.py`); each passed on
  an individual rerun, and #341 also failed on a clean base clone under the
  same validate environment. No failure touched the #374 contract surface.
  The affected suites above are green on the rebased candidate.
- KW K1 (sink dev-worktree cleanup typed refusal) is a follow-up in the
  Kaola-Workflow repository and is not part of this KPR candidate.
- KW K2 (located-but-refusing Runner blocking KW deletion) is an owner design
  decision and was not implemented. KW K3 (execution assertions for the
  finalize/sink refusal paths) is optional and not done.
- No release, tag, install, or cloud action was performed.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- scripts/validate.sh
- tests/contract/test-issue-374-worktree-guard-contract.py

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-374/.cache/final-validation.md
- kaola-workflow/archive/issue-374/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-374/finalization-summary.md
- kaola-workflow/archive/issue-374/mission-ledger.jsonl
- kaola-workflow/archive/issue-374/workflow-state.md
