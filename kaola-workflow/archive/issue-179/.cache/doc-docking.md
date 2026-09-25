# Documentation docking — issue-179

Candidate: workflow/issue-179 @ 10072ba (rebased onto main 636ab23; every
reviewed byte of the re-reviewed candidate preserved — non-CHANGELOG files
byte-identical to the reviewed 5f60f44, and CHANGELOG gained only main's #176
entry, kept alongside #179's per the Owner instruction).

Change class: a `reported_drift` vocabulary shrink plus a restart-set change in
one script, deferral of two prose surfaces to the field, contract-test
rewrites, and release-note bookkeeping. No protocol, adapter, manifest, or
holder byte changed.

Checked against AGENTS.md's documentation map and the issue's acceptance item 3:

- `CHANGELOG.md` — DOCKED: the Unreleased entry for #179 is the user-visible
  record (constant, removed values, the #166 reversal scoped to future
  releases, the `stale` consequence, and `Seats: restart not required` derived
  from the empty operator test over the restart set). Main's #176 entry is
  preserved beside it after the rebase; both were kept.
- `docs/api.md` — DOCKED: the `status`/`list` paragraph no longer enumerates
  `reported_drift` values; it names the field and keeps the restart-set list
  current (`kaola-quota.py` added).
- `docs/conventions.md` — DOCKED: the release-notes operator test now includes
  `scripts/kaola-quota.py`, with the reason (a holder pins that catalog at
  startup).
- `templates/references/acp.md.tmpl`, `templates/orchestrator/references/
  zcode-host-dispatch.md.tmpl`, `templates/orchestrator/references/
  host-startup.md.tmpl` — DOCKED: each refers to the `reported_drift` field
  instead of listing values; the ZCode stale list names `kaola-quota.py`.
  Rendered copies updated by `render-skills.py --write` and `--check` PASS
  byte-identical.
- `AGENTS.md` — DOCKED: the release command's operator test names
  `scripts/kaola-quota.py`.
- `README.md` — no impact: no entry layer, usage, or overview behavior changed;
  `reported_drift` is not a README-level concept.
- `docs/architecture.md`, `docs/zcode-host.md` — no impact: the holder/bridge
  topology and the ACP transport path are unchanged; this change narrows a
  reporting vocabulary and moves one file into the restart set.
- `docs/decisions.md` — no impact: no new decision record is owed; the Owner
  decision is recorded as the required comment on issue #179
  (issuecomment-5835739000), per acceptance item 9.

No public signature, JSON schema, or CLI help text changed beyond the removal
of two never-emitted receipt keys (`recorded_root`, `install_root`), which the
CHANGELOG entry states.

DOCKED
