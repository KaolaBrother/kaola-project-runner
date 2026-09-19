# Documentation docking — bundle-94 (Issue #94)

Candidate: `2fb5419` on `workflow/bundle-94` (production code `7714d98`).
Checklist source: `AGENTS.md` → Documentation Map + changed public behavior.

## Checked

| Surface | Verdict | What was docked / why no impact |
|---|---|---|
| `README.md` | FIXED | Installer guidance now names both default workspace discovery roots (`.zcode/skills` and `.agents/skills`) in the overview and the install examples. The Issue #92 permission-wake paragraph merged from `main` is present and untouched. |
| `CHANGELOG.md` | FIXED | Unreleased entry for Issue #94: the single native `/kaola-project-runner` entry on every turn-opening prompt, what it replaces from Issue #75, the live evidence, and the limits. Sits below main's Kimi 2.0.1 and Issue #92 entries; neither was altered. |
| `docs/zcode-host.md` | FIXED | Issue #75 compact-recovery section replaced by the native Skill entry section (mechanism, live-verified bullets, install precondition, boundaries, explicit not-verified list). `**Payload.**` names the holder-prepended entry line. Both Issue #92 bullets and the `idle_watcher` clause are preserved above it. |
| `docs/api.md` | FIXED | `--runtime zcode` destination text names the verified default roots; the `--steer-mode interrupt` section states the resend is verbatim on every session, is NOT a Host recovery entry, and that a caller wanting a Host round supplies the entry line itself. |
| `docs/architecture.md` | FIXED | ZCode Host paragraph names both default workspace discovery roots. |
| `scripts/install-local.sh` (`--help`) | FIXED | Help text lists the four default roots and states that configured `skills.roots` / `plugins.dirs` roots are scanned too. Transcribed from the shipped help, not invented. |
| `docs/codex-host.md` | NO IMPACT | Codex keeps its verified `SessionStart(compact)` hook; Issue #94 is a non-goal for other hosts. |
| `docs/grok-bot-host.md` | NO IMPACT | Bridge host is unchanged; it still loads Kaola-Delegator, which now opens its ZCode Host handoff with the native entry — covered in the Delegator reference, not here. |
| Generated `skills/` + `hosts/grok-bot/` | NO IMPACT (regenerated) | Never hand-edited. `render-skills.py --write` was a no-op after the rebase and `--check` PASS; the rendered `references/zcode-native-skill-entry.md`, `host-startup.md`, `zcode-host-dispatch.md`, `heartbeat-skeleton.md` and `kaola-delegator/references/handoff.md` carry the docked wording. |
| Environment / setup / validation policy in `AGENTS.md` | NO IMPACT | No new dependency, command, or validation policy. `validate.sh` gained the Issue #94 suite and kept the Issue #92 suite; both are in the existing lists. |

## Boundaries kept in the docs, not softened

- Native busy `steer` is the supported Host mid-turn path; the composite
  `--steer-mode interrupt` resend is explicitly NOT a Host recovery entry.
- The four `.zcode`/`.agents` workspace+user roots are DEFAULTS, not the whole
  surface; configured `skills.roots` and `plugins.dirs` roots also scan, and a
  `--skills-dir` outside every discovered root still arrives as plain text.
- Mock-provider evidence proves discovery and wire metadata, never model
  behaviour. Real-GLM automatic compaction is recorded as not claimed.

## Status

DOCKED
