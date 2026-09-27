# Documentation Docking — issue-194

Checked: README.md ("What Runner does" now states the testing-vs-QA distinction with a pointer
to `references/qa-evidence.md` in `kaola-project-runner`; the Kaola-Delegator entry-table row now
names the pacing-feedback duty), CHANGELOG.md (Unreleased bullet added for #194: testing/QA
distinction, evidenced-redundancy trigger, Delegator pacing clause, content-stage note),
templates/orchestrator/SKILL.md.tmpl and templates/kaola-delegator/SKILL.md.tmpl (source of the
generated Host/Delegator guidance itself — the change under docking), docs/grok-bot-host.md and
docs/conventions.md (grepped for "testing"/"QA"/pin-cadence text; no reference to the acceptance
flow or Delegator cadence exists there to update — the one hit was a substring of "attesting",
unrelated), AGENTS.md and the four-tier README entry (no change to Runner/Workflow contract
surface, transport, or session lifecycle; QA is Host judgment inside the existing acceptance step,
not a new layer, so the layered-entry description is unaffected).
No other doc impact: no CLI flag, API, config schema, install command, or transport behavior
changed; the change is Skill-prose guidance plus one new reference file, rendered normally.

DOCKED
