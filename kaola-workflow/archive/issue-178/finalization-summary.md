# Finalization Summary — issue-178

Issue: #178 — remove the transport seat-stale send/steer gate and
`--confirm-stale`; stale stays a status fact.
Branch: `workflow/issue-178` (originally `5041a6e` on base `0c3d200`; rebased
onto `3455e4f` as candidate `4c1a63d` after #174 landed).
Sink: merge.

## Delivered

Removed the #162 seat-stale send/steer transport gate entirely — the
classifier that blocked previously working automation — keeping `stale`,
`stale_reasons`, `restart_files`, and `reported_drift` as pure `status`/`list`
facts:

1. **Source removal.** `refuse_if_stale` (42 lines) and both send/steer call
   sites deleted from `scripts/kaola-acp.py`; `--confirm-stale` deleted from
   its argparse; the flag's four sites deleted from `scripts/kaola-tmux.sh`
   (variable init, case arm, the send/steer-only check, the pass-through).
   The `seat_freshness` docstring now says `stale` "is true only for" the
   restart-required set instead of "blocks dispatch".
2. **Policy stays, mechanics reworded.** The orchestrator templates keep "Do
   not dispatch a `stale: true` seat" and "replace it with `drain-restart`
   at idle"; the `--confirm-stale` mechanics became "an operator-confirmed
   exception on that one `send`/`steer` is the orchestrator's own call; there
   is no flag" (`templates/orchestrator/SKILL.md.tmpl`,
   `templates/orchestrator/references/zcode-host-dispatch.md.tmpl`).
3. **Transport docs stop describing a gate.** The "`send` and `steer` refuse
   `seat-stale` unless `--confirm-stale` is passed. `stop` and `status` are
   not gated." sentences removed from `templates/references/acp.md.tmpl` and
   `docs/api.md` (which also drops "or refuse a dispatch").
4. **Behavior evidence replacing the gate tests** (in
   `tests/contract/test-issue-162-upgrade-safety.py`, where the gate tests
   lived):
   `test_a_stale_flagged_seat_still_transports_send_and_steer` — a seat whose
   `status` reports `stale: true` (holder bytes changed on disk;
   `restart-required` + `kaola-acp-holder.py` in `restart_files`) delivers
   `send --no-wait` (`outcome: in_progress`, exit 0) and `steer`
   (`steer_outcome: injected`, `steer_consumed: true`), and the same seat's
   `status` still reports `stale`, `stale_reasons`, `restart_files`, and
   `reported_drift`;
   `test_delegator_handoff_shape_delivers_to_a_stale_host_seat` — the exact
   `handoff.md.tmpl` command shape (`"$ZCODE" send --repo "$PROJECT"
   --session "$HOST" --no-wait --text '<handoff>'` via the installed zcode
   `runtime-tmux.sh`) delivers to a stale Host seat, exit 0, delivered
   receipt, with no flag or remedy text.
5. **Gate tests updated minimally, names accurate.**
   `test_stale_blocks_only_the_restart_required_set` →
   `test_stale_marks_only_the_restart_required_set` (status-facts only; the
   refusal assertions and the vacuous `seat-stale` reason checks removed);
   the `--confirm-stale` template assertion removed from
   `test_release_note_rule_and_no_rebind_wording`;
   `tests/contract/test-issue-168-drift-enumeration.py` now asserts the
   five-value enumeration against real `seat_freshness` logic
   (`test_one_stale_seat_reports_all_five_drift_values`) instead of the
   deleted refusal detail.
6. **Rendered copies regenerated** (`./scripts/render-skills.py --write`),
   re-run after the rebase; `--check` PASS with budgets OK, all ten worker
   copies byte-identical to `scripts/`.

Net lines excluding rendered copies: **+119/−122 (−3)** — a removal, as the
owner rules require.

Independent review: Claude Code review `VERDICT: PASS for issue #178` — gate
removal verified complete and net-negative; acceptance granted.

## Files Changed

51 paths, +175/−777 total; excluding the 42 rendered copies +119/−122 (−3):

- `scripts/kaola-acp.py` (+1/−55)
- `scripts/kaola-tmux.sh` (+0/−6)
- `templates/orchestrator/SKILL.md.tmpl` (+4/−3)
- `templates/orchestrator/references/zcode-host-dispatch.md.tmpl` (+2/−2)
- `templates/references/acp.md.tmpl` (+1/−1)
- `docs/api.md` (+2/−3)
- `tests/contract/test-issue-162-upgrade-safety.py` (+62/−18)
- `tests/contract/test-issue-168-drift-enumeration.py` (+34/−34)
- `CHANGELOG.md` (+13, the #178 Unreleased entry)
- `skills/**` × 42 (re-rendered, byte-identical to source via
  `./scripts/render-skills.py --write` + `--check`, PASS)

No frozen surface (`templates/grok-golden/`, `hosts/`), no adapter, bridge,
holder, or `platforms/` file changed by this branch. The operator test
`git diff 3455e4f 4c1a63d -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/adapters platforms`
is empty, so the entry's `Seats: restart not required` line is accurate.
`tests/contract/test-issue-98-dsh-acp.py` was never touched (the concurrent
#174 seat owned it).

## Test Coverage

- Focused stale-gate-adjacent suites green on the reviewed candidate
  (`5041a6e`): `test-issue-162-upgrade-safety.py` 22/22 OK (including the
  two new transport tests), `test-issue-165-path-drift.py` 6/6 OK (no update
  needed — it asserts status facts only), `test-issue-168-drift-enumeration.py`
  1/1 OK; re-run green after the trim pass and again after the rebase.
- Full `./scripts/validate.sh` on the pre-rebase candidate
  (`/tmp/kpr-i178-validate.log`): every suite green except the then-known
  #174 flake `test-issue-98-dsh-acp.py` (`acp-initialize-timeout` instead of
  `acp-initialize-failed`, under the #174 seat's own concurrent validate
  load); focused re-run of that suite green 37/37. The #174 fix has since
  landed (`d7a3fc2`).
- **Final full `./scripts/validate.sh` on the rebased candidate `4c1a63d`
  (`/tmp/kpr-i178-validate-final.log`): exit 0, zero `FAILED` lines, zero
  `SKIPPED` — fully green.** The #98 flake did not appear (fix landed via
  #174) and the separate known `test-issue-65-host-contract.py` cursor-anchor
  flake (#176) did not appear either, so no flake-exception record is owed.
- Render gate: `./scripts/render-skills.py --check` PASS (run twice: after
  the original render and again after the rebase re-render), byte budgets
  OK, all ten worker copies of every shared script byte-identical to
  `scripts/`.
- Token acceptance: no `refuse_if_stale` / `seat-stale` / `--confirm-stale` /
  `confirm_stale` anywhere in the tree outside CHANGELOG history (verified on
  the committed candidate and again after the rebase).

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
- scripts/kaola-tmux.sh
- skills/claude-code-kaola-project-runner/references/acp.md
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-tmux.sh
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/references/acp.md
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-tmux.sh
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/references/acp.md
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-tmux.sh
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/references/acp.md
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-tmux.sh
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/references/acp.md
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-tmux.sh
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/references/acp.md
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-tmux.sh
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/references/acp.md
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-tmux.sh
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/zcode-host-dispatch.md
- skills/kimi-cli-kaola-project-runner/references/acp.md
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-tmux.sh
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/references/acp.md
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-tmux.sh
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/references/acp.md
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-tmux.sh
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/zcode-host-dispatch.md.tmpl
- templates/references/acp.md.tmpl
- tests/contract/test-issue-162-upgrade-safety.py
- tests/contract/test-issue-168-drift-enumeration.py

## Documentation Docking

`.cache/doc-docking.md` — **DOCKED**. `CHANGELOG.md` carries the #178
Unreleased entry stating **`Seats: restart not required.`**, verified
against the empty operator-test diff myself (only per-call CLI files,
templates, docs, and tests changed). `docs/api.md` and the worker
command-surface template dropped the gate sentences; the orchestrator
templates keep the dispatch policy with the flag mechanics reworded; the
Delegator handoff template needed no change (its exact command shape now
delivers to a stale Host seat, proven by contract test). `README.md`,
`docs/zcode-host.md`, and the architecture docs carry no gate statement
(token-verified), so no other doc needed an update.

## Follow-Up Items

- None filed by this run. The S2–S4 follow-ups the issue itself names are
  already filed: #179 (`reported_drift` vocabulary shrink; it will rewrite
  `test-issue-168-drift-enumeration.py`), #180 (single start-decision site),
  #181 (mode recording, `drain-restart` slimming). No run-discovered defect
  beyond them.
- No flake exceptions to record: the final full validate on `4c1a63d` is
  fully green — neither the #174/#98 flake (fixed on main) nor the #176
  `test-issue-65-host-contract.py` cursor-anchor flake appeared.

## Readiness

Acceptance: Claude Code review `VERDICT: PASS for issue #178` (gate removal
verified complete and net-negative). Candidate frozen at `4c1a63d` (rebased
onto `3455e4f`), worktree clean, rendered copies regenerated and
byte-identical. Final validation recorded: `verdict: pass`, command
`./scripts/validate.sh` (exit 0, zero `FAILED` lines), bound to candidate
tree hash
`40b50486438d9a02f6d32f46bfff59482ba0cbc79ccf26a97882d1f65e080a12`
(`.cache/final-validation.md`). Ready to archive, sink-merge
`workflow/issue-178` to main (no PR, no release/tag/pin), and close #178
referencing the review PASS.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-178/.cache/doc-docking.md
- kaola-workflow/archive/issue-178/.cache/final-validation.md
- kaola-workflow/archive/issue-178/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-178/finalization-summary.md
- kaola-workflow/archive/issue-178/mission-ledger.jsonl
- kaola-workflow/archive/issue-178/workflow-state.md
