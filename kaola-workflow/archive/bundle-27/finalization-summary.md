# Finalization Summary

## Delivered

Issue #27: local ACP watch `follow` on the holder Unix socket. `kaola-acp <platform> follow --repo … --session … [--since CURSOR] [--format json|text]` keeps a long-lived connection and writes NDJSON `{kind:snapshot|delta|heartbeat|eof|error}`. Snapshot/delta reuse `kaola-acp-view/1`. After the first `follow` op that FD is read-only. Per-follower queue cap 256 drops only that path (`follow-dropped`) without pausing agent stdio. Every `session/update` (including `tool_call`) applies the projection then fans out a cursor delta. Killing the follow CLI does not stop holder/agent. Agent exit emits `eof`; a dead holder emits `holder-lost`. `kaola-tmux.sh … follow` is `follow-unsupported`. L0 receipts and view one-object schema unchanged. `templates/grok-golden/` frozen.

## Files Changed

`scripts/kaola-acp-holder.py`, `scripts/kaola-acp.py`, `scripts/kaola-tmux.sh`, `scripts/validate.sh`, `templates/references/acp.md.tmpl`, generated Skills, `tests/contract/test-acp-follow-contract.py`, `tests/contract/mock-acp-agent.py`, README, CHANGELOG, `docs/api.md`, `docs/architecture.md`, `docs/README.md`, `docs/acp-watch/README.md`, `docs/acp-watch/follow.md`.

## Test Coverage

- `tests/contract/test-acp-follow-contract.py` 12 OK (was RED 11 FAIL on unimplemented `follow`; added `tool_call_only` plus SIGSTOP slow-consumer).
- `tests/contract/test-acp-watch-contract.py` 10 OK.
- `tests/contract/test-acp-contract.py` 18 OK.
- `./scripts/render-skills.py --check` PASS (6 Skills).
- `./scripts/validate.sh` PASS at hash `63351cdfef3f7c709615e5458148c148bb275f49ef29e64b7d0ef8253de3a707`, commit `7a58094`.
- Live tmux smoke / live CLI UAT against real agent binaries was not executed.
- `install-local.sh` not re-run in this finalize (owned bin links were #26).

## Validation

`./scripts/validate.sh` — PASS, candidate hash `63351cdfef3f7c709615e5458148c148bb275f49ef29e64b7d0ef8253de3a707`.

`git diff --stat templates/grok-golden` — empty.

Issue #27 acceptance: snapshot then increasing-cursor deltas; two followers see the same `tool_call`; follow-FD `prompt`/`permit`/`cancel`/`stop` are `kind=error` with no extra agent-stdin frames; third socket `permit`; slow follower `follow-dropped`; kill follow CLI leaves holder/agent; `process_exited` then `eof`; holder-lost error line; `--format text` joins titles; `validate.sh` green. Covered by the follow contract plus `validate.sh`. Heartbeat cadence is unpinned (shape checked when a heartbeat appears).

## Changed Paths

finalize `--check` `changed_paths`:
`scripts/kaola-acp-holder.py`, `scripts/kaola-acp.py`, `scripts/kaola-tmux.sh`, `scripts/validate.sh`, generated Skill `references/acp.md` plus `scripts/kaola-acp-holder.py` / `kaola-acp.py` / `kaola-tmux.sh` for all six platforms, `templates/references/acp.md.tmpl`, `tests/contract/mock-acp-agent.py`, `tests/contract/test-acp-follow-contract.py`.

`git diff --name-only origin/main...HEAD` also includes `CHANGELOG.md`, `README.md`, `docs/README.md`, `docs/acp-watch/README.md`, `docs/acp-watch/follow.md`, `docs/api.md`, and `docs/architecture.md`.

## Documentation Docking

DOCKED in `.cache/doc-docking.md`.

## Follow-Up Items

None.

## Readiness

READY for all-or-nothing closure and merge sink of issue #27.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/bundle-27/.cache/doc-docking.md
- kaola-workflow/archive/bundle-27/.cache/final-validation.md
- kaola-workflow/archive/bundle-27/.cache/implement-verify.md
- kaola-workflow/archive/bundle-27/.cache/mirror-digest.json
- kaola-workflow/archive/bundle-27/.cache/origin/selection-record.json
- kaola-workflow/archive/bundle-27/.cache/repair-verify.md
- kaola-workflow/archive/bundle-27/.cache/review-correctness.md
- kaola-workflow/archive/bundle-27/.cache/review-test-custody.md
- kaola-workflow/archive/bundle-27/.cache/review-trust-boundary.md
- kaola-workflow/archive/bundle-27/.cache/tdd-red-proof.md
- kaola-workflow/archive/bundle-27/finalization-summary.md
- kaola-workflow/archive/bundle-27/mission-list.md
- kaola-workflow/archive/bundle-27/workflow-state.md
