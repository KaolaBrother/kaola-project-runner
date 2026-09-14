# Finalization summary — bundle-39 (issue #39)

## Delivered

Optional expected-holder-instance binding on ACP `permit`/`cancel` per the frozen additive contract
in https://github.com/KaolaBrother/kaola-project-runner/issues/39 (coordinates KaolaTerminal #255).

- `Holder` mints `holder_instance_id = secrets.token_hex(16)` at construction — immutable for the
  process, never restored from record/native session id, never PID-derived.
- Exposed on `record.json`, `op_state` (status/observe), `op_view` payload top level (view + follow
  snapshot/delta/heartbeat), `kaola-acp-list/1` rows, and the `start` receipt.
- `--expected-holder-instance-id` forwarded verbatim (incl. explicit empty) by `kaola-acp.py` on
  permit/cancel/key-escape and by `kaola-tmux.sh`; compared inside `self.lock` before any
  settlement/cancellation/turn mutation/outbound cancel, including when nothing is active.
- Mismatch → `error.code=holder-instance-mismatch`, `expected_holder_instance_id` +
  `holder_instance_id` (actual) in the error object, `mutation_status=not_started` +
  `mutation_performed=false` (top level and in the error object), zero agent writes, plus an
  additive `holder_instance_mismatch` evidence event.
- Omitted flag = legacy behavior. Runner envelope only — never forwarded into native ACP params.

## Files Changed

- `scripts/kaola-acp-holder.py`, `scripts/kaola-acp.py`, `scripts/kaola-tmux.sh`
- `tests/contract/test-acp-contract.py` (new `Issue39HolderInstanceTests`, 6 tests)
- `tests/contract/fixtures/kaola-acp-view-1.sample.json`
- `docs/api.md`, `docs/acp-watch/list-view.md`, `docs/acp-watch/permit-lock.md`, `CHANGELOG.md`
- `skills/*/scripts/{kaola-acp.py,kaola-acp-holder.py,kaola-tmux.sh}` ×7 regenerated

## Test Coverage

Issue39HolderInstanceTests 6/6 pass: same-triplet restart reused request_id stale permit/cancel/
key-escape mismatch with zero agent writes and intact pending/turn; correct-binding and omitted-flag
success; explicit-empty not downgraded; identity on all projections; native resume mints fresh id;
concurrent bound permit still at-most-once; shell wrapper forwarding incl. empty.

## Validation

See `.cache/final-validation.md` — verdict pass on candidate hash 42be226b… at b950c0a.
Commands: Issue39+Issue25 tests (10 OK), Issue25+AcpContract (17 OK), acp-watch contract (13 OK),
render --write/--check (7 Skills PASS), ./scripts/validate.sh exit 0.

## Changed Paths

scripts/kaola-acp-holder.py, scripts/kaola-acp.py, scripts/kaola-tmux.sh,
tests/contract/test-acp-contract.py, tests/contract/fixtures/kaola-acp-view-1.sample.json,
docs/api.md, docs/acp-watch/list-view.md, docs/acp-watch/permit-lock.md, CHANGELOG.md,
skills/claude-code-kaola-project-runner/scripts/*, skills/codex-kaola-project-runner/scripts/*,
skills/cursor-cli-kaola-project-runner/scripts/*, skills/devin-kaola-project-runner/scripts/*,
skills/grok-kaola-project-runner/scripts/*, skills/kimi-cli-kaola-project-runner/scripts/*,
skills/opencode-kaola-project-runner/scripts/*

## Documentation Docking

DOCKED — see `.cache/doc-docking.md`.

## Follow-Up Items

None filed. Pre-existing suite hygiene note (not from this change): Issue34 codex/cursor-cli ACP
test holders can outlive their tempdir when torn down under the wrong platform name; observed as
leaked processes during validate.sh, cleaned exactly by PID for this run's tempdirs only.

## Final readiness

STOPPED BEFORE MERGE by explicit instruction — supervisor (Codex) reviews PR #40 and coordinates
Terminal integration. Close/archive/sink and any issue closure deferred until acceptance.
v0.1.0 tag untouched; no release created.

- PR: https://github.com/KaolaBrother/kaola-project-runner/pull/40
- Branch: workflow/bundle-39
- Commit: b950c0aded4c5f983971809198026023f2f39741

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/bundle-39/.cache/doc-docking.md
- kaola-workflow/archive/bundle-39/.cache/final-validation.md
- kaola-workflow/archive/bundle-39/.cache/mirror-digest.json
- kaola-workflow/archive/bundle-39/.cache/origin/selection-record.json
- kaola-workflow/archive/bundle-39/finalization-summary.md
- kaola-workflow/archive/bundle-39/mission-list.md
- kaola-workflow/archive/bundle-39/workflow-state.md
