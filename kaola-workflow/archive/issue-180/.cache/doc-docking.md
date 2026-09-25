# Documentation docking — issue-180

Candidate: workflow/issue-180 @ 36d765f (directly on main 8ab96d7; origin/main
unmoved at finalize time; no rebase owed).

Change class: consolidation of the start decision inside one script (the
refusal path drops the `--version` probe, folding #171 and resolving #172),
contract-test updates, and release-note bookkeeping. No protocol, adapter,
manifest, holder, or template byte changed.

Checked against AGENTS.md's documentation map and the issue's acceptance:

- `CHANGELOG.md` — DOCKED: the Unreleased entry for #180 records the
  consolidation (`command_start`'s five never-firing refusal branches deleted,
  `pre_spawn_refusal` returning the alignments and heartbeat resolution it
  computed for reuse, Skill roots hashed once per `start`), the `--version`
  refusal-path drop (superseding #171, resolving #172), and
  `Seats: restart not required` derived from the empty operator test over the
  restart set. #179's entry is preserved below it.
- `docs/api.md` — no change owed: its `runtime_binary` fact list already
  scopes the `--version` line to `preflight` ("… and on `preflight` the
  `--version` line"), which this change makes exactly true for every caller —
  `preflight` reports `version`, a refused `start`/`drain-restart` does not
  and never waits on the runtime binary. The grok `cli_version` paragraph is
  the successful-start transport probe (#124), untouched by this change. The
  `drain-restart` paragraph ("runs the start pre-spawn refusals before it
  stops; a refusal there leaves the seat up") is unchanged in meaning.
- `README.md` — no impact: no entry layer, usage, or overview behavior
  changed; the start decision is not a README-level concept.
- `docs/architecture.md` — no impact: the holder/bridge topology and the ACP
  transport path are unchanged; this change moves a decision inside one
  script and removes a probe from one refusal path.
- `docs/conventions.md` — no impact: the operator-test and release-notes
  rules are already followed by the CHANGELOG entry's Seats line; the release
  pin rules are not triggered (no tag, no pin, no release).
- `docs/zcode-host.md` — no impact: its refusal surfaces (#106 root/skew,
  #108 Host model pin, #126 host entry, #130 transport) are refusal reasons
  and receipts this change does not alter; none claims `--version` or
  preflight parity for the refusal path.

No public signature, JSON schema, or CLI help text changed beyond the
refusal receipt no longer carrying `version` (`preflight` unchanged), which
the CHANGELOG entry states.

DOCKED
