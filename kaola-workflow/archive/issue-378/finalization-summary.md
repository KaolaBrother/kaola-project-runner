# Finalization Summary — issue-378

## Delivered

The cwd-repair notice is delivered once per turn on a platform whose native steer confirms only
the write. `scripts/kaola-acp-holder.py` adds `cwd_steer_delivered()`: `injected`, or
`written`/`queued` with `mutation_performed: true`, is delivery once for that turn, and
`_cwd_notice_delivered` then clears `notice_paths` and the batch stamp. dsh's
`_session/steering` answers `written`; the old `== "injected"` test left the notice pending and
`idle_watcher` re-steered the whole batch every 15 s for the rest of the turn.

`_cwd_deliver_notice` also keeps a per-turn backstop: one `turn.request_id` (falling back to the
turn's `started_at` during admission) never steers the same `notice_paths` batch twice, even when
a receipt cannot be marked as delivery. That notice stays `pending` and rides the next boundary's
self prompt.

The notice text is stable across retries. `_cwd_notice_text` reads one `notice_ts` stamp set when
the batch is first staged, persists it in `record.json`'s `tool_cwd`, reuses it on every retry and
on resume, and clears it when the batch is delivered, so the text and `steer_fingerprint` no
longer churn. A V2 pre-emption while the shell cwd is unobserved stages a new batch and gets its
own steer after an earlier batch was delivered; a multi-path batch is still one steer naming every
repaired path.

`tests/contract/mock-acp-agent.py` gains the `written` and `queued` steering outcomes. The new
`tests/contract/test-issue-378-cwd-notice-delivery.py` (registered in `scripts/validate.sh`) drives
a real holder against that mock: a two-path `written` batch is delivered once and the next 15 s
tick sends nothing; a V2 pre-emption after a delivered batch is still steered and delivered once;
and the delivery predicate, stable text and resume restore are asserted directly. `docs/api.md`
documents the delivery rule and `notice_ts`; `CHANGELOG.md` Unreleased carries the #378 entry with
`Seats: restart required`. Generated Skill copies were re-rendered.

## Candidate

Branch `workflow/issue-378` at `68afbc9523bcb0f8f98bce37d44fce5a7c0aba51`. Main is unchanged at
`082d9ced` (equal to `origin/main`, 0/0 divergence), so the branch already sits on current main
and no rebase was needed. The merge is a fast-forward of that accepted candidate. Generated Skill
copies render cleanly (`./scripts/render-skills.py --check` PASS) and `git diff --check` is clean.
The Grok Bot bridge remains at the unpinned content stage on main.

## Evidence

- Host acceptance in conversation of `68afbc95`: delivery predicate (`injected`, or
  `written`/`queued` with `mutation_performed: true`), same-`turn.request_id` batch dedupe,
  persisted `notice_ts` stability, V2 pre-emption batches, `--steering written`/`queued` mock
  cases, affected subset green, render check PASS, live evidence re-checked.
- Final affected subset on the frozen candidate `68afbc95`:
  `./scripts/validate.sh --suite test-issue-378-cwd-notice-delivery.py ...` (10 suites:
  #378, #369 holder cwd repair / cwd vanished / worktree guard, #374, #341, #255,
  `test-acp-contract`, `test-acp-holder-continue`, #263), exit 0, total wall 384.5 s, log
  `/tmp/kpr378-final-subset.log`. This is a **SUBSET RUN**, not full-inventory coverage; the
  suites outside this diff-scoped list were not run.
- `test-issue-378-cwd-notice-delivery.py` 5/5 tests, 82.5 s; `render-skills.py --check` PASS;
  `git diff --check` clean.
- Live evidence re-checked read-only in
  `/tmp/kaola-501/dsh/dsh-KPR-i373-cwdtrace/ffd858d3940f076a/events.jsonl`: 499 `steer_result`
  rows, 499/499 `steer_outcome: written`, ~5.4 h apart at the 15 s cadence; all three
  `tool_cwd_notice_delivered` rows are `via: worker-event`, none `via: steer` — the F1 loop and
  the old delivery test exactly as diagnosed.
- Final validation record: `kaola-workflow/issue-378/.cache/final-validation.md`, verdict
  `pass`, validated candidate hash
  `3c0452db592696cffa726acd079b66a8abb6e62a92f33f4ec4f0711e55676bff`, command
  `./scripts/validate.sh --suite test-issue-378-cwd-notice-delivery.py --suite test-issue-369-holder-cwd-repair.py --suite test-issue-369-cwd-vanished.py --suite test-issue-369-worktree-guard.py --suite test-issue-374-worktree-guard-contract.py --suite test-issue-341-agent-initiated-turn.py --suite test-issue-255-lifecycle-state.py --suite test-acp-contract.py --suite test-acp-holder-continue.py --suite test-issue-263-steer-adaptation.py`.

## Known failures or unverified scope

- The validation evidence is a diff-scoped subset (10 suites), deliberately not the whole
  inventory. Full-inventory coverage is not claimed.
- The adjacent #378 findings F2 (tier C `observed_at` is sample time), F3 (`_cwd_error_set` churn
  while git cannot answer) and F4 (stale docstring) are LOW/INFO in the issue body and remain
  unaddressed; the issue itself marked them non-gating.
- No new live dsh/ZCode run was performed for this fix. The behaviour is proven by the mock-ACP
  contract and the recorded dsh session, whose 499 written results are the reproduction.
- `Seats: restart required`: `scripts/kaola-acp-holder.py` is in the operator restart set, so a
  running seat keeps the re-steer behaviour until it restarts. No install, tag, release, cloud
  action, or other Host restart was performed.

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
- tests/contract/mock-acp-agent.py
- tests/contract/test-issue-378-cwd-notice-delivery.py

## Follow-Up Items

- None filed by this run. F2/F3/F4 are already recorded in the #378 body as non-gating
  observations; no new defect was discovered during finalization.

Readiness: accepted candidate, affected subset green, ready to merge and archive.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-378/.cache/final-validation.md
- kaola-workflow/archive/issue-378/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-378/finalization-summary.md
- kaola-workflow/archive/issue-378/mission-ledger.jsonl
- kaola-workflow/archive/issue-378/workflow-state.md
