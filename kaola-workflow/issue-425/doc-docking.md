# Document docking of issue #425
- format: kpm.workflow-doc-docking/1.0
- issue: 425
- candidate:
- checked_by:
- checked_at:
- verdict:

## Impact
- scripts/kaola-dispatch.py | Host terminal write (verdict accepted or cancelled, one cite) deletes the task; row-scoped 512-byte and disposition-orphan checks; unchanged duty facts do not write
- scripts/kaola-record-contract.py | shared DUTY_STRING_MAX_BYTES, duty_string_offenses, and disposition_orphan_paths
- scripts/validate.sh | registers test-issue-425-prevent-invariants.py in python_suites_all and python_suites_b
- tests/contract/test-issue-425-prevent-invariants.py | new writer contract suite for the settled P1, P3/A2, A1, and P5 rows
- templates/orchestrator/references/lifecycle-state.md | terminal deletion, 512-byte bound, dispositions subset of dispatch
- templates/orchestrator/references/heartbeat-skeleton.txt | same vocabulary in the generated Host body guide
- CHANGELOG.md | Unreleased #425 bullet; Seats: restart required
- skills/ | regenerated copies of the dispatch script, record contract, lifecycle-state, and heartbeat-skeleton

## Docking
