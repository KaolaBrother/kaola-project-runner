# #272 loop execution evidence — real run (2026-10-07, this session)

The working-method link (qa-evidence @5cef759a) executed end-to-end on three real findings; no JSON fields/scheduler/ledger added.

## Finding 1: entry-coverage gap (symptom: phase-1 zero-dispatch)
- Attribution (per hypothesis): H1 planning/role (role: primary, status: confirmed — comment 6030420812); H2 contract friction (role: contributing, confirmed — two real refusals); H3 tool failure (refuted — zero admission attempts).
- QA class: coverage-insufficiency (assertion-proof: test-issue-244:3706-3720 re-read).
- Minimal design: D1/D2 (batch 1). Independent verification: oracle+render+budget suites (real and green). The six-step behavioral acceptance was initially cited here; its PASS has been WITHDRAWN (@91373205) — the standing parts (admission/collection/guarded-stop receipts, guard-id hop) remain verification of steps 4-5 only; text/suite-level evidence covers 1-3 until the isolated fixture rerun. Host adoption: committed 5cef759a, shipped-to-main (NOT installed; see P0 honesty).
- Observation: recurrence watch = the six-step fixture itself re-run at next fresh Host (named condition: discovery hops stay 0); retreat = git revert (text-only).

## Finding 2: PID-reuse false agent_alive (#273)
- Attribution: H1 list-projection copy (primary, confirmed — :923/:894 source); H2 status path (open — unverified); H3 stop-kill risk (refuted — no evidence stop kills wrong process).
- QA class: not-covered (no fixture existed).
- Minimal design: verified-only projection reusing holder_identity+anchor (batch 1). Independent verification: bridge 8/8 real-entry + 6/6 consumer QA (externally produced), landed as real-entry suite (e7aea057 non-vacuous). Host adoption: 5cef759a/e7aea057.
- Observation: consumer seats re-checked via delegator view (unknown never releases); retreat = revert commits (no data migration).

## Finding 3: package closure (#274)
- Attribution: single hypothesis (dynamic-load helper absent from package), confirmed by git cat-file at 3de9f61.
- QA class: not-covered.
- Minimal design: render copy closure (batch 2). Independent verification: bridge-executed 4/4 (isolated positive + dependency-named failure + guards). Host adoption: 93662173.
- Observation: next render+release is the recurrence check (named condition: helper present in shipped package); retreat = revert render change.

## FP discipline demonstrated
No finding was marked FP without refuting evidence; H3s above stayed OPEN/refuted explicitly, not false-positived. The 273 vacuous-pass incident itself entered the loop as a finding (attribution: fixture repo mismatch, primary confirmed) and was repaired with a negative control (e7aea057).
