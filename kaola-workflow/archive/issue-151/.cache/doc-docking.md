DOCKED

Checked every documentation surface against the changed behavior (#151:
skip-with-receipt on missing dev-machine prerequisites for the full contract
suite):

- README.md — UPDATED: one prerequisites line in "Validation and evidence"
  (tmux, bash >= 4 mapfile/BASHPID, python >= 3.10; a missing prerequisite
  skips the affected rows with a named receipt).
- AGENTS.md — UPDATED: one Validation Policy bullet with the same facts,
  inside the managed project-facts region.
- CHANGELOG.md — NO CHANGE by issue scope: #151 explicitly requires no
  version bump and no CHANGELOG release entry.
- docs/api.md — NO IMPACT: no command, receipt, or transport surface changed;
  the three changed surfaces are developer test rows plus the watchdog
  wrapper.
- docs/architecture.md, docs/conventions.md — NO IMPACT: conventions.md's
  generic `render-skills.py --write && validate.sh` invocation makes no
  machine-requirement claim; architecture is unchanged (dev/test-only
  surfaces).
- docs/ dated evidence records (live smoke, PoC, design docs) — NO IMPACT:
  historical records of past runs, not statements about current machine
  requirements.
- README examples — NO IMPACT: no example output changed.
