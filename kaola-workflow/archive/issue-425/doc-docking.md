# Document docking of issue #425
- format: kpm.workflow-doc-docking/1.0
- issue: 425
- candidate: 6cef870244e60cd12df189ead3c64643da259870
- checked_by:
- checked_at:
- verdict:

## Impact
- scripts/kaola-dispatch.py | Host terminal write deletes the task; any other merged stage done is stage-done-refused; a touched string must land within 512 bytes; merged disposition orphans refuse; unchanged duty facts do not write
- scripts/kaola-record-contract.py | shared DUTY_STRING_MAX_BYTES, duty_string_offenses, and disposition_orphan_paths
- scripts/validate.sh | registers test-issue-425-prevent-invariants.py in python_suites_all and python_suites_b
- tests/contract/test-issue-425-prevent-invariants.py | writer contract suite for the settled P1, P3/A2, A1, and P5 rows, including the repair pins
- templates/orchestrator/references/lifecycle-state.md | terminal deletion, 512-byte bound, dispositions subset of dispatch
- templates/orchestrator/references/heartbeat-skeleton.txt | same vocabulary in the generated Host body guide
- CHANGELOG.md | Unreleased #425 bullet; Seats: restart required
- skills/ | regenerated copies of the dispatch script, record contract, lifecycle-state, and heartbeat-skeleton

## Docking
