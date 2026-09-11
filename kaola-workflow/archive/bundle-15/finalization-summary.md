# Finalization Summary: Issue #15 — ACP transport PoC

## Delivered

- Prototype ACP transport for the Runner v2 dual-transport design:
  `scripts/kaola-acp.py` (socket-client CLI: preflight, start, send, wait,
  observe, capture L0–L3, permit, key escape→cancel, cancel, stop [--force],
  status) and `scripts/kaola-acp-holder.py` (per-session holder: spawn with
  `start_new_session`, NDJSON JSON-RPC reader, stderr pump, pending-permission
  map, five-state `mutation_status`, §7.6 stop sequence, §3.2 record dir,
  short-path AF_UNIX socket with record-dir symlink).
- Offline contract suite: `tests/contract/mock-acp-agent.py` (12 scripted
  scenarios) + `tests/contract/test-acp-contract.py` (13 tests) wired into
  `scripts/validate.sh`; covers every branch in design §7.3/§7.4/§7.6.
- Live validation on both PoC platforms: Grok 1.0.25 (`grok agent stdio`) and
  Kimi 0.41.0 (`kimi acp`); per-scenario evidence in
  `kaola-workflow/bundle-15/evidence/part-b-grok.md` and `part-b-kimi.md`.
- Token-cost measurement: `evidence/measure.py`, `part-c-raw.json`.
- Published PoC report: `docs/poc-acp-transport-2026-09-11.md`.

## Files Changed

- `scripts/kaola-acp.py`, `scripts/kaola-acp-holder.py` (new, prototype)
- `tests/contract/mock-acp-agent.py`, `tests/contract/test-acp-contract.py` (new)
- `scripts/validate.sh` (one line: run the acp contract suite)
- `docs/poc-acp-transport-2026-09-11.md` (new report)
- `docs/README.md`, `README.md`, `CHANGELOG.md` (docking)

No manifest, template, adapter, installer, or `kaola-tmux.sh` changes;
`templates/grok-golden/` untouched; `skills/` unchanged.

## Test Coverage

- 13/13 offline contract tests green, covering all 10 issue Part-A branches
  (permission-pending agent death, half/non-JSON lines, stderr flood,
  cancel↔end_turn race, `$/cancel_request` both directions → -32800,
  protocolVersion 2 refusal, `fs/*`/`elicitation` → -32601, numeric-string ids,
  concurrent permissions, residual-free stop).
- Live Grok: 11/13 scenarios PASS; #2 permission requests never emitted
  (`always-approve` mode — auto-approves); #6 login path
  PRECONDITION-NOT-MET (already authenticated; `login_required:false` reported
  with authMethods).
- Live Kimi: 11/13 PASS; same #2/#6 status (mode=default emits no
  request_permission in 0.41.0).
- Token measurement: 5 runs each transport, task "reply PONG"; medians —
  acp 2,453 B / 791 cl100k / 3 invocations / 0 observations / 7.9 s;
  pty 29,982 B / 9,313 cl100k / 6 invocations / 3 observations / 13.1 s.
  ≈12× byte and token reduction, 2× fewer invocations, 1.7× faster.
  `mutation_status` accurate in all runs; 0 recovery attempts.

## Validation

- `python3 ./scripts/render-skills.py --check` → PASS (6 Skills)
- `bash ./scripts/validate.sh` → PASS (incl. new acp suite 13/13)
- Recorded: `.cache/final-validation.md` bound to worktree hash
  `fb114c0f…` at commit `71eb800`.
- pty live smoke unchanged: `kaola-tmux.sh` untouched; exercised live during
  scenario 7 (pty resend) — works identically.

## Changed Paths

- scripts/kaola-acp.py
- scripts/kaola-acp-holder.py
- scripts/validate.sh
- tests/contract/mock-acp-agent.py
- tests/contract/test-acp-contract.py
- docs/poc-acp-transport-2026-09-11.md
- docs/README.md
- README.md
- CHANGELOG.md

## Documentation Docking

`.cache/doc-docking.md` → DOCKED.

## Follow-Up Items

- Run-discovered gaps filed as issues (see finalize transaction record):
  cross-transport prompt journal for duplicate-prompt-warning; permission-gating
  investigation before acp becomes default; production v2 implementation
  (manifests, templates, installer wiring).
- Decision input ready: whether the remaining four platforms default to acp.

## Readiness

All five missions done; all applicable acceptance green; the two unexercised
legs (#2 live permission, #6 logout→login) are documented platform/precondition
facts, not unverified claims.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/bundle-15/.cache/doc-docking.md
- kaola-workflow/archive/bundle-15/.cache/final-validation.md
- kaola-workflow/archive/bundle-15/.cache/mirror-digest.json
- kaola-workflow/archive/bundle-15/.cache/origin/selection-record.json
- kaola-workflow/archive/bundle-15/evidence/measure.py
- kaola-workflow/archive/bundle-15/evidence/part-b-grok.md
- kaola-workflow/archive/bundle-15/evidence/part-b-kimi.md
- kaola-workflow/archive/bundle-15/evidence/part-c-raw.json
- kaola-workflow/archive/bundle-15/finalization-summary.md
- kaola-workflow/archive/bundle-15/mission-list.md
- kaola-workflow/archive/bundle-15/workflow-state.md
