# Documentation Docking — Issue #187

Status: DOCKED

Checked against `AGENTS.md`'s documentation checklist for changed public behavior.

| Surface | Decision | Reason |
|---|---|---|
| `templates/kaola-delegator/` (SKILL, `references/handoff.md.tmpl`, new `references/host-platforms.md.tmpl`, `references/host-brick.md`) | **Updated** (source) | The external Skill now selects any supported CLI Host: platform Runner, exact `host_skill_entry`, standard `<platform>-<PROJECT_CODE>-orchestrator-<purpose>` name, per-platform native resume id, beat-level startup proof, non-zcode Grok Bot attestation boundary. Rendered via `render-skills.py --write`; `--check` PASS. |
| `skills/kaola-delegator/**`, `skills/kaola-project-runner/SKILL.md`, `skills/*/scripts/main-skill-build.json` | **Regenerated** | Generated output only, never hand-edited. Budgets: SKILL 4075/4096 B, description 318/320 chars, handoff 8186/8192 B, host-platforms 4653/8192 B, host-brick 909/8192 B. |
| `templates/orchestrator/SKILL.md.tmpl` | **Updated** (two sentences) | "start or continue a ZCode Host" / "starts one ZCode Host" were made false by #187; now platform-neutral. Moves the main Skill build id (recorded in CHANGELOG). |
| `hosts/grok-bot/*` | No change | Bridge byte-identical (sha256 `54fbdf39…08ef`), content stage unchanged; it was already platform-neutral. |
| `scripts/install-local.sh` (help text) | **Updated** | Help text transcribes the new behavior: Codex/generic plan `kaola-delegator` whatever `--platform` selects. |
| `README.md` | **Updated** | Status paragraph (any of ten Host platforms; Host platform apart from worker authorization), A→B recovery identities, Grok Bot locator `--worker <Host platform>`, bridge paragraph, locator comment on liveness, installer note. |
| `AGENTS.md` | **Updated** | Project Snapshot and Layered entry no longer state a ZCode-only Delegator Host; native resume id generalized; locator `--worker <Host platform>`. |
| `CHANGELOG.md` | **Updated** | One `## Unreleased` entry: any-Host selection, installer change, bridge unchanged, Grok Bot UAT unverified, codex-acp 1.13.1 narrow fact, main Skill build id moves (reinstall). No release section, no `Seats:` line (release-only). |
| `docs/architecture.md`, `docs/conventions.md`, `docs/grok-bot-host.md` | **Updated** | ZCode-only Delegator Host wording corrected; Grok Bot attestation `--worker` set to the Host's platform. |
| `docs/host-entry-evidence.md` | **Updated** | Codex row version cell names the 1.13.0 measurement; new note records the Host-reported codex-acp 1.13.1 E2 `SKILL-NOT-LOADED` fact and the owner acceptance of the live Codex Host, not re-measured in #187. |
| `docs/zcode-host.md` | **Updated** | The Host-name shape citation now points at `host-platforms.md.tmpl`, where the string lives. |
| `docs/api.md`, `docs/codex-host.md` | No change | No API field, receipt field, or Codex hook behavior changed; the locator and Runner CLIs are unchanged. |
| `docs/harness-acp-compat-2026-09-2*.md` | No change (out of scope) | Untracked operator files in main, preserved. |

No invented fields, signatures, or schema were transcribed; `host_selection`, `host-exists`,
`holder-instance-mismatch`, `native_session_identity`, and locator reasons match
`scripts/kaola-acp.py`, `scripts/kaola-acp-holder.py`, and `scripts/kaola-locate.py`.
