# Finalization Summary — issue-358

## Delivered

Issue #358 (bookkeeping 4b): a Host whose carrier record advertises `sideagent-node/1` default-binds Sideagent node mode at `state init` and at holder startup, including this repository's own Host. The binding uses an eligible granted Worker: the Delegator file's `authorization.sideagent.preset` when that id is already eligible, otherwise the first granted Worker by id. `computer-use-only` roles and exclusions are skipped. An existing binding is kept, including across resume. The bind does not raise `host_revision` and is not a node input. When no eligible preset exists or the runner cannot be built, `sideagent` stays unset and `state check` reports `sideagent-default-unbound` with the `state ensure-sideagent` command. The recovery-route table names that command. The next Host boundary retries.

Obsolete positioning text is removed from the project instructions, the README, docs, comments, fixtures, and archive prose. The project overview keeps one current sentence, once in `AGENTS.md` Purpose and once at the README opening.

`CHANGELOG.md` Unreleased has the #358 bullet after the #353, #354, #355, #357, and #356 bullets. The section line stays `Seats: restart required`. The operator diff `a5ac6c9d..5cd5d2c3` lists only `scripts/kaola-acp-holder.py`. The Grok Bot bridge stays unpinned (`saveable: false`).

## Candidate

Branch `workflow/issue-358`, parent `a5ac6c9de54dbb8a6ae461da5f3a37d93b6316c3`.

- `5cd5d2c33a61d4f5c7f6fa663c52d165fdff1f59` — `Bind Sideagent node mode by default at Host entry (#358)`

85 files changed, 1723 insertions, 453 deletions. Acceptance candidate: `5cd5d2c3`. Worktree clean. This finalize adds no implementation commit.

Host acceptance: ACCEPTED in the controlling conversation on 2026-10-19, with the boundary below.

## Evidence

- Focused suite `./scripts/validate.sh --suite test-issue-255-lifecycle-state` in the worktree, `KAOLA_LAUNCH_BACKEND=direct`, proxies and `KAOLA_ACP_DISPATCHER` / `KAOLA_ZCODE_ENTRY` / `KAOLA_ZCODE_NODE` unset: 166 tests OK, exit 0. The later full inventory re-ran that suite in 159.463 s and did not list it under `FAILED:`.
- Fixture suites after the text edits, same launch backend: `test-issue-296-shared-tier-seats.py` Ran 10 OK; `test-issue-324-wake-fixes.py` Ran 10 OK; `test-issue-302-delegator-wake-gate.py` Ran 38 OK.
- `./scripts/render-skills.py --check` PASS. After the template edit, `--write` then `--check` PASS. `templates/orchestrator/references/sideagent-node.md` is 8175 bytes.
- Full inventory in the worktree, recorded in `.cache/final-validation.md` as verdict fail. Command and result are under Known failures. The tree was dirty on parent `a5ac6c9d` while that inventory ran; the commit `5cd5d2c3` followed about one minute later and the worktree is clean at that commit.
- Evidence comments: issuecomment-6263742231 (before fixture and archive text edits), issuecomment-6265073265 (delivery).

## Known failures and unverified scope

- Acceptance exception: the full inventory is not green. `./scripts/validate.sh` (color variables, proxies, `KAOLA_ACP_DISPATCHER`, `KAOLA_ZCODE_ENTRY`, and `KAOLA_ZCODE_NODE` unset; `NO_COLOR=1`; `KAOLA_LAUNCH_BACKEND=direct`) printed `FULL INVENTORY (133 suites)`, one `FAILED:` line for `test-issue-309-recovery-routes.py`, and `validate: total wall: 1623.59 s`. The script exits 1 when a suite lane returns non-zero. The missing `ROUTES` codes are `checked-out`, `done-not-retired`, `entry-needs-one-verb`, `live-session`, `returned-unreadable`, `state-bloat`, and `unmerged-or-unpushed`. `sideagent-default-unbound` is not missing.
- The same seven codes were printed by `python3 tests/contract/test-issue-309-recovery-routes.py` from the main checkout (`Ran 8 tests`, `FAILED (failures=1)`). That gap is pre-existing on baseline `a5ac6c9d`. It is filed as #364. This candidate does not add `ROUTES` rows for those seven codes.
- No release, tag, or install in this finalize.
- Live ACP smoke per platform was not re-run for this change.

## Validation

classification: final_validation_failed
green: false
mode: final-validation

.cache/final-validation.md does not record `verdict: pass` (column 0) — the agent's own validation did not pass (found verdict: fail)

.cache/final-validation.md is present but does not record `verdict: pass` (column 0). The agent's own validation did not pass — remediate and re-record, or fix the failing checks before finalize.

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- AGENTS.md
- CHANGELOG.md
- README.md
- docs/api.md
- docs/ddd/README.md
- docs/ddd/cases/vrpai-cad-analysis.md
- docs/ddd/context-map.md
- docs/ddd/packs/c1-exact-stop.md
- docs/ddd/packs/c4-state-retire.md
- docs/ddd/packs/kw-c8-seam.md
- docs/host-compact-capabilities.md
- docs/kpm-transfer/HANDOFF.md
- docs/kpm-transfer/RETIREMENT-RECEIPT-2026-10-07.md
- docs/release-candidate-2026-10-08/rqa-clean-render.log.txt
- docs/release-candidate-2026-10-08/rqa-clean-validate.log.txt
- scripts/kaola-acp-holder.py
- scripts/kaola-dispatch.py
- scripts/kaola-kw-index.py
- scripts/kaola-recovery-routes.py
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/antigravity-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/sideagent-node.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/references/sideagent-node.md
- tests/contract/test-issue-255-lifecycle-state.py
- tests/contract/test-issue-296-shared-tier-seats.py
- tests/contract/test-issue-302-delegator-wake-gate.py
- tests/contract/test-issue-324-wake-fixes.py

## Follow-Up Items

- filed: #364. Labels `bug` and `P3` were set on create. Confirmed open, body length 2562 (non-empty). https://github.com/KaolaBrother/kaola-project-runner/issues/364
- searched: `repo:KaolaBrother/kaola-project-runner is:open missing ROUTES` hit 0; `is:open recovery routes ROUTES` hit 1 (#358); `test-issue-309 in:title,body` hit 1 (#321, closed); `done-not-retired state-bloat in:body` hit 1 (#354, closed); `is:issue checked-out done-not-retired entry-needs-one-verb` hit 1 (#358).
- No release, tag, or install in this finalize.

## Readiness

Host accepted `5cd5d2c3` with the #309 exception boundary above. Merge sink into main, push to origin, close issue #358, archive, remove the branch tail and the worktree. Do not tag, release, or install.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-358/.cache/final-validation.md
- kaola-workflow/archive/issue-358/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-358/finalization-summary.md
- kaola-workflow/archive/issue-358/mission-ledger.jsonl
- kaola-workflow/archive/issue-358/workflow-state.md
