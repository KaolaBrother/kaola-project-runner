# Documentation docking — issue #162

DOCKED

Checked against AGENTS.md Documentation Map and the public behavior this run changed.

- `CHANGELOG.md` — Unreleased #162 states build identity, the restart-required stale set, pin and CLI drift as report-only, drain-restart, locate intent scope, and `Seats: restart required` with the operator diff. Fix: already in the candidate.
- `docs/conventions.md` — Release notes section is the operator rule the stale gate matches. Fix: already in the candidate.
- `docs/api.md` — `runner_build`, blocking `stale`, `reported_drift`, `baseline_exempt`, PATH pin lookup, and drain-restart pre-stop / post-stop mutation facts. Fix: already in the candidate.
- `docs/zcode-host.md` — Keeps "there is no rebind operation" and "A live holder is never hot-replaced", and adds drain-restart beside them, including the restart-required versus pin/CLI split. Fix: already in the candidate.
- `AGENTS.md` — Release bullet names the same operator test and the two seat-restart lines. Fix: already in the candidate. The layered-entry locator sentence still names `--project --worker zcode --session` and refuse-any-`refused`. The `--intent start|resume` split is the generated handoff the bridge loads (`templates/kaola-delegator/references/handoff.md.tmpl`), not a second copy in AGENTS.md. No-impact: the sentence does not contradict the split.
- `README.md` — Still points ACP transport, permission, and receipt detail at `docs/api.md`. No command-surface dump added. No-impact.
- `docs/architecture.md` — No new component, registry, or hot-rebind path. No-impact.
- Examples — Generated `references/acp.md`, `zcode-host-dispatch.md`, and `host-startup.md` carry the command surface. They are rendered output of the templates above. No-impact beyond that render.
- Setup / environment — No new variable the operator must export. `KAOLA_ACCEPTED_REVISION` is holder argv, not an agent environment variable. No-impact.

No documentation file was edited during finalization. The candidate bytes stay the validated tree.
