# Finalization summary — issue-293

## Delivered

Fix for #293: the Host carrier finds its bound Sideagent node's record
across every ACP record root, and a verified `session-exists` refusal
adopts or defers to the live holder instead of orphaning it.

- `scripts/kaola-acp-holder.py`: new `_node_directory` resolves the node
  session through `acp_paths.find_directory(..., all_roots=True)` with the
  Host's own root first; `_sideagent_relay_target`, `_node_record` and
  `_stop_node` use it (previously single-root). The node-start failure
  branch now distinguishes: a verified `session-exists` naming a live
  sideagent-role holder this carrier dispatched → adopt (`phase=running`,
  holder recorded, no status overwrite); a live holder another holder
  dispatched → `stop_unconfirmed` plus a registered stop duty
  (`old-node-live`); anything else keeps the original one-failure branch.
  A live node's status is never overwritten by a refusal.
- `scripts/kaola-acp-paths.py`: `directories`/`find_directory` gain an
  `all_roots` keyword (explicit root stays first; without it the explicit
  root keeps its exclusive scoped view — covered by a dedicated test).
- Tests: new `tests/contract/test-issue-293-node-record-roots.py` (8 cases:
  all-roots resolution in legacy TMPDIR/explicit root, scoped-view
  back-compat, node record in legacy and fixed root, adopt own-dispatched,
  defer foreign-dispatched, unverified keeps failure) driving the real
  holder in-process with planted records; suite registered in
  `validate.sh`. CHANGELOG Unreleased entry (restart required).
- Scope decisions recorded: the maintenance-tool `KAOLA_ACP_RECORD_ROOT`
  pin at holder L3504 is deliberately kept (that call writes as the Host's
  own dispatcher identity, whose record lives in the Host's root; the
  scoped view is correct); there is no holder-side separate
  `node_is_running` (node liveness goes through `_node_record`, now
  multi-root); the holder does not force the node's record location — it
  gains visibility across roots instead of env-forwarding its own root.

## Candidate

- Implementation commit `aea87547` on `workflow/issue-293` (worktree
  `.kw/worktrees/issue-293`, base `2a22c81b` = current main). Implemented
  by the `devin/opus-fusion` seat `devin-KPR-i293-holder-roots`; reviewed
  and finalized by the Host.

## Evidence

- Host diff review (this run): both Expected items of the issue verified
  against the code; adoption/defer semantics behavior-tested.
- `./scripts/render-skills.py --check` — PASS.
- Affected suites in the candidate worktree, all exit 0:
  `test-issue-293-node-record-roots.py` (new), `test-issue-255-lifecycle-state.py`,
  `test-issue-292-state-record-root.py`, `test-issue-278-record-root.py`,
  `test-issue-289-dead-holder-stop.py`, `test-issue-268-selection-continuity.py`
  (logs `/tmp/kpr-i293-*.log`).
- `.cache/final-validation.md`: verdict `pass`, candidate hash
  `e40f03bcc2b5bfdd2f310d0c415733e6d3213b60291420f265dbbef421e8f014`.
- Worker seat exact-stopped after acceptance (`state: stopped`; ACP list
  shows only the Host row live).

## Known failures / unverified scope

- Full `validate.sh` inventory not re-run for this issue alone: the whole
  inventory passed on `b1e47cd4`/`2a22c81b` during #292 close-out, and the
  holder change is covered by the six affected suites above. The full
  inventory runs once at the release boundary over the integrated
  candidate (#292+#293+#294+#295), per the repo's evidence-reuse policy.
- Per-platform live ACP smoke is carried as a release-boundary duty, as in
  the #292 summary.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- scripts/kaola-acp-holder.py
- scripts/kaola-acp-paths.py
- scripts/validate.sh
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-paths.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp-paths.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-paths.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp-paths.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp-paths.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp-paths.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp-paths.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/scripts/kaola-acp-paths.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-paths.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp-paths.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp-paths.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- tests/contract/test-issue-293-node-record-roots.py

## Follow-Up Items

- None filed (no new KPR issues per owner directive 2026-10-07). The
  unbound-Host maintenance-registration observation remains reported to
  the owner in the run report (see issue-292 summary).

## Final readiness

Ready: candidate reviewed, affected scope green, validation recorded.
Proceed to sink (merge) and archive.
