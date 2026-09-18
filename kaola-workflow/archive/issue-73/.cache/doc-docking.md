# Documentation docking — Issue #73

Status: DOCKED

Changed public behavior: one new environment binding
(`KAOLA_PROJECT_RUNNER_CANONICAL_REPO`), two new typed refusal reasons
(`canonical-root-mismatch`, `canonical-root-invalid`), one new receipt field
(`canonical_repo`), and `--expected-holder-instance-id` now honored on `stop`.

| File | Result |
|---|---|
| `README.md` | Fixed. New `### Orchestrator binding` subsection between `### Normal path` and `### Evidence-backed exception`: the export, omitted-`--repo` completion, the refusal and its `mutation_performed: false`, the `canonical_repo` receipt fact, and that an existing session keeps its own `--repo`. |
| `CHANGELOG.md` | Fixed. New entry at the head of `## Unreleased`, transcribed from the shipped behavior. |
| `docs/api.md` | Fixed. Two paragraphs after the `--repo`/session-syntax paragraph: the binding's effect on `--repo`, the literal refusal JSON shape, and `--expected-holder-instance-id` across `permit`/`cancel`/`key`/`stop` with the `holder-instance-mismatch` error shape. |
| `docs/architecture.md` | Fixed. Paragraph appended to `## Canonical project root and Workflow child worktrees`, naming `scripts/kaola-tmux.sh` as the single entrypoint that resolves the binding, the realpath comparison, the typed refusals, and what is unchanged without the export. |
| `docs/conventions.md` | No impact. Carries the Issue #52 canonical-root guidance markers; this change adds no new convention there, and the #52 contract suite still passes. |
| `docs/zcode-host.md` | No impact. ZCode Host surface, untouched by this change (Issue #70 owns it). |
| `templates/orchestrator/SKILL.md.tmpl` | Fixed as source, not documentation: states the binding once in place of per-dispatch path-proving prose. |
| `templates/orchestrator/references/workflow-worktree.md` | Fixed as source: new `## Orchestrator binding` section; the manual re-proof prose it replaces was removed. |
| `templates/orchestrator/references/heartbeat-skeleton.txt` | Fixed as source: the binding and the instance-exact stop named once on the repo/goal line. |
| `templates/orchestrator/references/host-startup.md.tmpl` | Deliberately NOT changed. Its five `"$WORKER" <op> --repo "$PROJECT" --session <name>` lines are pinned verbatim by Issue #72's live test; editing them reaches outside Issue #73. Section A is ordinary standalone worker supervision, where the binding does not apply. |
| `AGENTS.md` | Deliberately NOT changed. Its last Runner-contract bullet still describes the ordinary canonical-root default, which remains true; adding the Orchestrator binding there is a project-contract edit outside this Issue's necessary file set. Flagged for the owner. |

All transcription is from the shipped code and the tests that exercise it; no
field, flag, or output was invented.
