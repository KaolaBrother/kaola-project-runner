# Finalization Summary — bundle-153 (Issue #153)

Candidate: workflow/bundle-153 @ 7d8bce7 (frozen; validated_candidate_hash
4d0d89e4eae4fe9227fe825db3677a96a24e442f7379593d10d0e31b1b595dbc)
Run posture: single-issue run on Mac Studio (this seat droid worker, session marker
s-4233-muesr2hq, droid-default); worktree .kw/worktrees/bundle-153.

## Delivered

Issue #153 "harness-compat 2026-09-24(class 2): Codex 0.156.1 + codex-acp 1.13.1 pin,
zcode-acp 0.47.x precheck" — a record-only Pink admission, no release cut, no local CLI
upgraded, `~/.dsh` untouched:

1. Codex pins per the Pink class-2 report: `platforms/codex.yaml` `acp_command` →
   `@openai/codex@0.156.1` + `@agentclientprotocol/codex-acp@1.13.1`, `acp_verified_versions` →
   `cli=0.156.1;adapter=1.13.1;protocol=1`, `acp_wrapper_pin` → `1.13.1`. The #145 stale note
   (npm 0.156.1 uninstallable on the 2026-09-23 measuring network) is superseded in `acp_quirks`
   with record-only provenance; the dated 2026-09-23 measurements stay. Hardcoded copies synced:
   `test-runner-v2.py`, `test-issue-22-bypass-all-approvals.py`, the `test-acp-contract.py`
   #145 comment, and the host-entry-matrix codex row (measured 1.13.0, cell names pinned 1.13.1
   with provenance).
2. zcode-acp 0.47.x precheck, verified read-only via authenticated `gh api` (network open):
   0.47.x exists through v0.47.10 (2026-09-23); v0.47.3/#244 and v0.47.4/#247 hold prompts
   during auto-compact and report the window busy; v0.47.8/#255 (patch 58fbbe5 read directly)
   makes `compact()` the single busy-raise point for manual and auto compactions (turn-state
   running:true, `waitForAutoCompactIdle` hold, avoids the -32010 backend compact lock);
   v0.47.9/#257 `usage_update` reports context occupancy only. npm `zcode-acp` is unrelated
   (leezhian 0.1.0). NOT verified: any live 0.47.x run and whether the installed ZCode.app
   3.14.1 / CLI 0.16.9 backend emits the same semantics. ZCode stays `cli=0.16.9`, wrapper pin
   `80aa4e2`; `platforms/zcode.yaml` unchanged because the generated zcode ACP reference is at
   8179/8192 budget bytes, so the precheck record lives in
   `docs/harness-acp-compat-2026-09-24.md` §2 and the CHANGELOG entry.
3. Evidence doc `docs/harness-acp-compat-2026-09-24.md` (pins, precheck, optional records,
   bridge reset, validation receipts, `.kaola` receipt pointer) plus the local receipt
   `.kaola/harness-compat-2026-09-24.md` at the canonical root.
4. Optional same-commit records: kimi-cli `cli=2.1.0`, opencode `cli=2.0.15` (steering_summary
   names 2.0.15 as the un-probed record, keeping the 2.0.11 initialize observation and 1.18.17
   history; `test-issue-88-permission-defaults.py` record assertions synced), claude-code
   `cli=2.1.280`, droid `cli=0.225.1` (live `droid --version` = 0.225.1 rc 0 on this machine; no
   upgrade performed).
5. One CHANGELOG `## Unreleased` entry for the whole admission.
6. Bridge stage: first content commit after the v0.6.0 pin (bf718f7 → R 2504be21) returns
   `templates/grok-bot/accepted-revision.json` to the content stage (a74119a precedent) so
   render accepts post-pin work; bridge unpinned, `saveable: false`; no tag, no release.

## Files Changed

35 paths at 7d8bce7 vs main base db54017, +243/−76: CHANGELOG.md,
docs/harness-acp-compat-2026-09-24.md (new), platforms/{codex,kimi-cli,opencode,claude-code,
droid}.yaml, tests/contract/{test-runner-v2,test-issue-22-bypass-all-approvals,
test-acp-contract,test-issue-88-permission-defaults}.py,
templates/orchestrator/references/host-entry-matrix.md, templates/grok-bot/accepted-revision.json,
plus the regenerated `skills/` and `hosts/grok-bot/` products of those inputs.

## Test Coverage

- `./scripts/render-skills.py --write`: WROTE rc=0 (first attempt rc=1 under the active v0.6.0
  pin; resolved by the documented content-stage reset).
- `./scripts/render-skills.py --check`: PASS rc=0 (budgets OK, content stage, unpinned).
- `./scripts/validate.sh`: rc=0, zero FAILED/ERROR, 281 test rows ok, run twice (pre-commit and
  re-confirmed on the frozen committed tree); named prerequisite skip receipts only
  (python≥3.10 ×2 rows, tmux ×3 rows, bash≥4 watchdog lanes; machine: bash 3.2.57, Python
  3.9.6, no tmux) — assertions not weakened (#151 policy).
- No test was deleted, weakened, or reinterpreted; the only test edits move pinned record
  values with the manifests (test-runner-v2/test-issue-22 exact pin strings, test-issue-88
  cli=2.0.15 record pins).

## Validation

- `kaola-workflow-validation-runner.js record --project bundle-153 --verdict pass --command
  "./scripts/render-skills.py --check (rc=0) and ./scripts/validate.sh (rc=0), run separately
  from this worktree on the frozen candidate"` → receipt `validated_candidate_hash 4d0d89e4…`,
  `verdict: pass` in `.cache/final-validation.md`, hash binding the frozen worktree tree.
- No npm chains: consumer repo declares no `test:kaola-workflow:*` (finalize gates on the
  agent-recorded final-validation.md).
- Acceptance legs: automated/local validation above; Host acceptance recorded in conversation
  (render --check PASS rc=0 on the frozen tree, 35-file diff verified in-scope, validate rc=0
  receipts accepted). No live ACP leg: the issue is record-only by its own text.

## Changed Paths

The finalize transaction's own `changed_paths` report lands here at transaction time (all paths
this branch changed outside `kaola-workflow/` run state) — the 35-path list reported by the
finalize --check: CHANGELOG.md, docs/harness-acp-compat-2026-09-24.md, hosts/grok-bot/*
(3), platforms/* (5), skills/* (17), templates/grok-bot/accepted-revision.json,
templates/orchestrator/references/host-entry-matrix.md, tests/contract/* (4).

## Documentation Docking

DOCKED — `.cache/doc-docking.md`: CHANGELOG entry and the new evidence doc in place; README /
architecture / conventions / AGENTS.md no-impact reasons recorded; one stale api.md attribution
filed as follow-up #155 instead of patching the frozen accepted candidate.

## Follow-Up Items

- filed: #155 (P3, documentation) — `docs/api.md` opencode steering note still names
  `acp_verified_versions` 2.0.11 after the record moved to 2.0.15 in #153; one-sentence sync
  next pass. `searched:` probe actually run — grep over README.md, docs/architecture.md,
  docs/conventions.md, docs/api.md for every moved version string: 1 hit (api.md:450), filed.

## Readiness

READY — Host acceptance granted for 7d8bce7; single-issue close; sink-merge into main, issue
#153 closure with comment, `.kaola` receipt sink appendix, archive, and worktree cleanup
proceed next. The issue-154 run (claim, worktree, branch) is co-active under another seat and
is not touched by any step of this finalization.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/bundle-153/.cache/doc-docking.md
- kaola-workflow/archive/bundle-153/.cache/final-validation.md
- kaola-workflow/archive/bundle-153/.cache/origin/selection-record.json
- kaola-workflow/archive/bundle-153/finalization-summary.md
- kaola-workflow/archive/bundle-153/mission-ledger.jsonl
- kaola-workflow/archive/bundle-153/workflow-state.md
