# Document docking of issue #408
- format: kpm.workflow-doc-docking/1.0
- issue: 408
- candidate: b83cec31575e3d5b185d8a9887f7f1da165c4a3d
- checked_by: pending
- checked_at: pending
- verdict: pending

## Impact
- CHANGELOG.md | `## Unreleased` gains a `Fixes #408` clause in the fixes line and one bullet recording the bound-seat socket enforcement (holder-issued `auth.token` plus mandatory `expected_holder_instance_id` on mutating ops), the repair-round refusals (`invalid-token`, watchdog self-heal, `stop --force` fallback), and the Host-holder-first upgrade-order note; `Seats: restart required` is stated
- docs/api.md | the holder-socket section gains the #408 paragraph — the mutating-op gate, all four typed refusals (`unauthenticated`, `invalid-token`, `holder-instance-required`, `holder-instance-mismatch`), the `socket_op_refused` event, the delegator-source-by-design clarification, the watchdog self-heal and force-stop facts, and the unbound-seat scope; the compact-notice binding documents the new `record_dir` field
- scripts/validate.sh | the suite inventory registers `tests/contract/test-issue-408-bound-seat-socket-auth.py`
- README.md / docs/conventions.md / docs/decisions | no change: no command surface, schema, convention or architecture fact moved
- templates/ and skills/ | generated surfaces re-rendered from the changed scripts; no template or reference document text changed

## Docking
