# Finalization summary — Issue #73

Issue: #73, "enhancement: Pin Orchestrator worker dispatch to the canonical project root"
Branch: `workflow/issue-73`  ·  Sink: merge  ·  Base: main `0dacb07`

## Delivered

Two guarantees, both settled before any side effect exists.

**A. One canonical-root binding per Orchestrator run.** A Project Runner Orchestrator exports
`KAOLA_PROJECT_RUNNER_CANONICAL_REPO=<abs root>` once at setup. `scripts/kaola-tmux.sh` — the one
entrypoint both transports and all nine platforms already pass through, so no per-platform policy
fork and no second validator was needed — resolves that binding and the requested `--repo` with
`realpath`, requires the binding to be a Git top-level, completes an omitted `--repo` from it, and
on `start` compares the two exactly. A different root, a linked worktree of the same repository
included, returns `canonical-root-mismatch`; an unusable binding returns `canonical-root-invalid`.
Both carry `mutation_performed: false` and exit non-zero before any process, tmux session, socket,
or record exists. An accepted dispatch reports `canonical_repo` in its receipt.

The guard runs only when the binding is actually used — an omitted `--repo`, or a `start`. That
asymmetry is the design, not an omission: it is what keeps a legacy worktree-rooted session
observable and exactly stoppable by its own verified original locator, as the Issue's Preserve list
and the owner's fourth comment require.

**B. An instance-exact stop.** `scripts/kaola-acp.py` forwards the already-existing
`--expected-holder-instance-id` on `stop`, and the holder's `op_stop` checks it through the
already-existing `_holder_instance_mismatch` path before `stop_requested`, the state write,
permission cancellation, or any signal. A same-named session rebuilt by a later holder instance is
refused instead of stopped. Nine lines; no registry, lock, daemon, or multi-host arbitration.

Owner-correction order was load-bearing: the **单项目单编排者** comment overrides the earlier
two-Orchestrator ownership-isolation comment, so the per-Host owner mechanism and its tests that
comment had asked for were deliberately not built.

## Files Changed

Source: `scripts/kaola-tmux.sh`, `scripts/kaola-acp.py`, `scripts/kaola-acp-holder.py`,
`scripts/validate.sh`.
Prompt sources: `templates/orchestrator/SKILL.md.tmpl`,
`templates/orchestrator/references/workflow-worktree.md`,
`templates/orchestrator/references/heartbeat-skeleton.txt`.
Tests: `tests/contract/test-issue-73-canonical-root.py` (new).
Docs: `README.md`, `CHANGELOG.md`, `docs/api.md`, `docs/architecture.md`.
Generated: `skills/**` re-rendered from source; `templates/grok-golden/` untouched.

## Test Coverage

`tests/contract/test-issue-73-canonical-root.py`, 29 tests, registered in `scripts/validate.sh`
(all-list plus lane B). **16 failed on the recorded baseline** and all pass on the candidate.

The suite is hermetic by construction: `tmux` and every runtime binary resolve to paths that
cannot exist, so an accepted invocation dies at `tmux executable not found` while a refused one
says `canonical-root-*`. That contrast — not a bare non-zero exit — is what distinguishes the
guard from a generic error. Fixture: a real main checkout, two linked worktrees of it on one
origin, an unrelated repo, a symlink, and a non-root subdirectory. One live ACP dispatch runs the
offline mock agent end to end and reads the worker record off disk.

## Validation

- `verdict: pass`, command `./scripts/validate.sh`, recorded in `.cache/final-validation.md`.
- `./scripts/validate.sh` exit **0** on the rebased candidate; whole suite green, including Issue
  #67's and #70's suites and `render-skills.py --check`.
- `python3 scripts/render-skills.py --write` after the rebase produced **no diff**: the
  auto-merged generated output already equalled a clean render from source.

## Changed Paths

Reported by the finalize transaction (`finalize --check`, `ok: true`, `dirty_paths: []`,
`validation: chains_green`), 38 paths:

`scripts/kaola-acp-holder.py`, `scripts/kaola-acp.py`, `scripts/kaola-tmux.sh`,
`scripts/validate.sh`, `templates/orchestrator/SKILL.md.tmpl`,
`templates/orchestrator/references/heartbeat-skeleton.txt`,
`templates/orchestrator/references/workflow-worktree.md`,
`tests/contract/test-issue-73-canonical-root.py`, plus the 30 regenerated files under `skills/`
(`kaola-acp-holder.py`, `kaola-acp.py`, `kaola-tmux.sh` for each of the nine platform Skills, and
`SKILL.md`, `references/heartbeat-skeleton.md`, `references/workflow-worktree.md` for the
orchestrator Skill).

That list is measured against the implementation commit `38b177c`. The documentation docking landed
in the follow-on commit `e324c35` and additionally touches `README.md`, `CHANGELOG.md`,
`docs/api.md`, and `docs/architecture.md`.

## Acceptance criteria walk

1. *Binding established once, survives heartbeat resumption, visible in bounded dispatch evidence.*
   The binding is an exported environment fact of the Orchestrator's own process, so it survives
   heartbeat wakes without new state; `canonical_repo` appears on accepted receipts.
   Covered by `test_started_worker_record_carries_the_bound_root`.
2. *Every new Orchestrator worker record has `repo` equal to the bound root; a mismatch is rejected
   before mutation, even a linked worktree of the same repository.* Covered by
   `test_child_worktree_of_the_same_repository_is_refused`,
   `test_second_child_worktree_is_refused_too`,
   `test_dispatch_into_a_child_worktree_creates_no_worker_record`, and
   `test_refusal_happens_before_the_acp_agent_is_launched` (a marker file proves no agent process
   was spawned).
3. *Worker code may still run in an isolated Workflow worktree named in its prompt; same-issue
   sessions stay distinct under #72.* Unchanged by construction — the guard constrains only Runner
   `--repo`, never the worker's working directory — and the prose now says to name the child
   worktree in the prompt. Issue #72's suite is green.
4. *Existing sessions are not restarted or rewritten and keep `observe`/`stop`; no per-platform
   fork or daemon.* Covered by `test_legacy_worktree_rooted_session_can_still_be_stopped`,
   `..._can_still_be_observed`, `test_legacy_acp_session_can_still_be_captured`. One guard in one
   shared entrypoint; nothing added to any adapter.
5. *Skill/heartbeat prose shorter, payload still generated, render/size validation proves it;
   standalone ACP and PTY starts still work.* Rendered `skills/kaola-project-runner/`
   **57432 → 57246 bytes** measured at `0dacb07` vs the candidate; `render-skills.py --check`
   PASS. Standalone covered by `test_standalone_start_in_a_child_worktree_is_not_refused`,
   `test_standalone_acp_start_in_a_child_worktree_is_not_refused`,
   `test_empty_binding_is_not_orchestrator_context`, and
   `test_standalone_omitted_repo_still_fails_as_before`.

Owner-added scope (start and stop share one context; no wrong-instance stop) is covered by the
five `TestStopInstanceProtection` tests, including force-stop and the shell-entrypoint passthrough.

## Documentation Docking

`DOCKED` — see `.cache/doc-docking.md`.

## Follow-Up Items

- **No independent clean-context review of the final candidate was obtained.** The `code-reviewer`
  dispatched against the pre-rebase SHA `a066a80` never returned — it was stopped when the previous
  session ended and produced no findings. The outer reviewer's ACCEPT of `a066a80` stands on its
  own independent review. The post-rebase candidate differs from `a066a80` only by the merge of
  `0dacb07` and the doc docking, and is fully re-validated, but it was never itself
  independently reviewed. Recorded here rather than silently dropped.
- `AGENTS.md`'s Runner-contract bullet still states only the ordinary canonical-root default. It is
  not wrong, but an owner may want the Orchestrator binding named there; editing the project
  contract was outside this Issue's necessary file set.
- `templates/orchestrator/references/host-startup.md.tmpl` still spells `--repo "$PROJECT"` on all
  five worker example lines, because Issue #72's live test pins those lines verbatim. Under the
  binding those examples could omit `--repo`; changing them needs #72's test to move with them.

No new defects were discovered during this run that warrant filing, and no correction to the Issue
text is needed — the Issue's own analysis held up against the code.

## Sink record

- Mainline: `0dacb07..7911a91`, pushed. Published head `e324c35c54ebf8c112d251df9ab3be4a6ae110bc`;
  `7911a91` is the sink's own archive commit.
- Issue #73 CLOSED at 2026-09-18T12:45:00Z. Remote branch `workflow/issue-73` deleted; local branch
  and worktree removed by the sink.
- Closure audit: `current_project_clean: true`, every drift counter 0 both in scope and outside it.
- Session close-out: no `i73-*` tmux session, holder process, or temp root remains. One holder had
  leaked from a standalone (non-`validate.sh`) run of this Issue's own suite - pid 14003, session
  `i73-test-standalone-acp-start-in-a-child-worktree-is-not-refused` - identified by three
  independent facts (its binary path under this run's removed worktree, its `i73-` session name,
  its `kaola-i73-` record root). Its graceful socket `stop` answered `holder-closed` and its record
  root was already gone, so it was ended with the sweeper's documented `SIGTERM` fallback, scoped to
  that single-member process group. No other session's holders (30 running) or tmux session were
  touched.
- Run-discovered defect filed: **#77** (P3), confirmed OPEN with a 2212-byte body - the test above
  starts an ACP holder it never stops. `validate.sh` is unaffected because its TMPDIR-scoped sweep
  catches it; only standalone runs leak.

## Readiness

Sunk and closed. Validation pass recorded, docs docked, acceptance criteria walked.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-73/.cache/doc-docking.md
- kaola-workflow/archive/issue-73/.cache/final-validation.md
- kaola-workflow/archive/issue-73/.cache/mirror-digest.json
- kaola-workflow/archive/issue-73/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-73/finalization-summary.md
- kaola-workflow/archive/issue-73/mission-list.md
- kaola-workflow/archive/issue-73/workflow-state.md
