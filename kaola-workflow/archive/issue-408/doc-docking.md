# Document docking of issue #408
- format: kpm.workflow-doc-docking/1.0
- issue: 408
- candidate: 80c4db0b72089150fff28ed148b7401b96f526db
- checked_by: host
- checked_at: 2026-10-23T03:43:00Z
- verdict: docked

## Impact
- CHANGELOG.md | `## Unreleased` gains a `Fixes #408` clause in the fixes line and one bullet recording the bound-seat socket enforcement (holder-issued `auth.token` plus mandatory `expected_holder_instance_id` on mutating ops), the repair-round refusals (`invalid-token`, watchdog self-heal, `stop --force` fallback), and the Host-holder-first upgrade-order note; `Seats: restart required` is stated
- docs/api.md | the holder-socket section gains the #408 paragraph — the mutating-op gate, all four typed refusals (`unauthenticated`, `invalid-token`, `holder-instance-required`, `holder-instance-mismatch`), the `socket_op_refused` event, the delegator-source-by-design clarification, the watchdog self-heal and force-stop facts, and the unbound-seat scope; the compact-notice binding documents the new `record_dir` field
- scripts/validate.sh | the suite inventory registers `tests/contract/test-issue-408-bound-seat-socket-auth.py`
- README.md / docs/conventions.md / docs/decisions | no change: no command surface, schema, convention or architecture fact moved
- templates/ and skills/ | generated surfaces re-rendered from the changed scripts; no template or reference document text changed

## Docking
- D1 | CHANGELOG.md | updated | `## Unreleased` documents the bound-seat socket enforcement, all four typed refusals, watchdog self-heal, `stop --force` fallback, `Seats: restart required`, and the Host-holder-first upgrade-order note
- D2 | docs/api.md | updated | holder-socket section describes the mutating-op gate, the four refusals, `socket_op_refused`, delegator-source-by-design, self-heal and force-stop facts, unbound-seat scope, and the binding's `record_dir` field
- D3 | scripts/validate.sh | updated | inventory registers `tests/contract/test-issue-408-bound-seat-socket-auth.py`; suite exercised at 28/28
- D4 | README.md / docs/conventions.md / docs/decisions | no-impact | no command surface, schema, convention or architecture fact moved
- D5 | templates/ and skills/ | no-impact | generated surfaces re-rendered byte-checked from changed scripts; no template or reference-document text changed
