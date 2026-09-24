# Finalization Summary — issue #161

## Delivered

`docs/api.md` now describes the **shipped** `--runtime kimi-cli` dual-root install (Issue #159)
instead of the pre-#159 single-root table. Exactly the two gaps named in the issue are closed:

1. **Destination table (line ~154).** The stale `kimi-cli` / `dsh` → `$HOME/.agents/skills` line
   is split: `dsh` stays single-root, and `kimi-cli` (Issue #159) is documented as installing into
   **BOTH** `$HOME/.agents/skills` (the cross-tool root, shared with `dsh`) and
   `${KIMI_CODE_HOME:-$HOME/.kimi-code}/skills` (the Kimi-specific root, which moves with
   `$KIMI_CODE_HOME`), **each with its own receipt set**.
2. **Reference-counting paragraph.** The legacy-referrer example (`kimi-cli,dsh` for
   `$HOME/.agents/skills`) is kept for the shared root, and the paragraph now states that a
   pre-ledger receipt in the **Kimi-specific** root counts as referenced by `kimi-cli` **alone**
   — its only installer — so a kimi-cli `--uninstall` withdraws the kimi-cli reference from
   **both** roots it owns: the shared root keeps its Skills while `dsh` still refers to them, and
   the Kimi-specific root removes them because no referrer remains.

Docs-only. No code, template, or generated surface touched; the frozen #159 work is untouched.

Implementation commit (frozen, rebased, reviewed): `4d22ffde235a2b594c06489f9197ce212b1f1e51`
(reviewed pre-rebase as `59fe96a2c25bee9eaad3c270074862c767074d54`; the rebase left the
`docs/api.md` blob sha `0fce6bb9f81a73216a40b28296b4a16b1020dc58` and sha256
`6583c74ed607aaebb968841d85985cfc6d6450fc296d94db97d5547a1e53ae0e` byte-identical).

## Files Changed

- `docs/api.md` (+9/−2): the destination table split and the expanded reference-counting
  paragraph described above. This is the branch's only change outside `kaola-workflow/` run state.

Run-state only (not part of the candidate): `kaola-workflow/kaola-project-runner/`
(workflow-state, `doc-docking.md`, `final-validation.md`, selection record) and
`kaola-workflow/.ledger/issue-161.jsonl`.

## Test Coverage

Docs-only change; no behavioral surface changed, so no product test target applies. Validation is
the generation/lint gate plus a live behavioral probe of the **documented** claims:

- `./scripts/render-skills.py --check` — **PASS**, exit 0, unchanged from the pre-change baseline
  (10 workers + kaola-project-runner + kaola-delegator + grok-bot host bridge; budgets OK).
  Run both directly and through `kaola-workflow-validation-runner.js run`
  (`exit_code: 0`, `candidate_digest` stable pre/post `60c73b0a…`).
- Live throwaway-`HOME` probe (shadow `HOME` + `KIMI_CODE_HOME`, since removed) against the
  shipped installer, confirming every documented claim:
  `install-local.sh --runtime kimi-cli` populated both roots, each receipt set `['kimi-cli']`;
  a subsequent `--runtime dsh` install made the shared-root referrers `['dsh','kimi-cli']`;
  `--runtime kimi-cli --uninstall` left the shared root
  `kept: … (still referenced by dsh)` with referrers `['dsh']` and **removed** the
  Kimi-specific root; after stripping `referrers` from the Kimi-specific receipts (pre-ledger
  simulation) the kimi-cli uninstall still removed them, confirming `kimi-cli`-only attribution.
- Claude Code review seat — **VERDICT PASS** on the frozen candidate (source-verified against
  `scripts/install-local.sh` @ `2c65758` plus a live throwaway-HOME install); 3 non-blocking
  minors recorded, deliberately not fixed in this run.
- `./scripts/validate.sh` not run: docs-only, no generated or executable surface changed, and
  `render-skills.py --check` is the repo's docs-relevant gate.

## Documentation Docking

DOCKED — see `.cache/doc-docking.md`. `docs/api.md` was the sole remaining stale surface;
`README.md`, `CHANGELOG.md`, and `docs/host-entry-evidence.md` were already updated by #159 and
carry no stale claim. No CHANGELOG entry is added for this correction: repo convention is that a
pure `docs/api.md` fix ships without one (precedent `9eb28d0`, #155), and #159's Unreleased entry
already documents the behavior this run documents.
## Follow-Up Items

- 3 non-blocking minors from the Claude Code review seat (recorded in the review verdict, not
  fixed here per the Host's explicit instruction).
- No new issue was filed: this run discovered no defect beyond the documentation staleness the
  issue already named.

## Readiness

Candidate frozen and reviewed; all three missions `done`; validation receipt `verdict: pass`;
docs docked. Ready for the sink transaction.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

none outside the kaola-workflow/ run-state band.

## Sink Findings

post_rebase_tests: skipped

archive_collision: kaola-workflow/archive/kaola-project-runner/ already existed, so this run was archived to kaola-workflow/archive/kaola-project-runner.archived-2026-09-24T16-18-30-273Z/ instead. The pre-existing directory was left exactly where it was — a SECOND archive standing for this project, no part of this one. What it holds, and whether the repository tracks it at all, is not recorded here: read it before treating this archive as the run's whole record.

archived_paths:
- kaola-workflow/archive/kaola-project-runner.archived-2026-09-24T16-18-30-273Z/.cache/doc-docking.md
- kaola-workflow/archive/kaola-project-runner.archived-2026-09-24T16-18-30-273Z/.cache/final-validation.md
- kaola-workflow/archive/kaola-project-runner.archived-2026-09-24T16-18-30-273Z/.cache/origin/selection-record.json
- kaola-workflow/archive/kaola-project-runner.archived-2026-09-24T16-18-30-273Z/finalization-summary.md
- kaola-workflow/archive/kaola-project-runner.archived-2026-09-24T16-18-30-273Z/mission-ledger.jsonl
- kaola-workflow/archive/kaola-project-runner.archived-2026-09-24T16-18-30-273Z/workflow-state.md
