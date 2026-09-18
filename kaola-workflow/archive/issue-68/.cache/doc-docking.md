# Documentation docking — Issue #68

status: DOCKED
candidate: 77a9ecf (docs) on top of accepted merge 19eda62
dispatched: inline, this session. `doc-updater` was not dispatched: the outer coordinator
authorized exactly one worker for this run, and the docking surface is two passages, so a handoff
would have cost more than it saved. Every line below was transcribed from the shipped text, not
invented.

Changed public behavior under review: the main Skill's heartbeat contract — per-host delivery
trigger, effective-now snapshot instead of a change log, same-beat effect of a user-confirmed
change, and the per-beat drop/keep subtraction rule. No API, CLI flag, receipt field, script,
manifest, transport, setup step or environment requirement changed, and no byte budget moved.

## Checked against AGENTS.md's documentation map

| File | Verdict |
|---|---|
| `docs/zcode-host.md` | **FIXED.** Line 135 still said a beat "updates the file (project info, pace, plans, coordination)" — the exact enumeration this run replaced with the skeleton's drop/keep rule. Now: rewrites the file as the next beat's snapshot, keeping only the constraints still in force per `references/heartbeat-skeleton.md` (Issue #68). The #66 sentences around it (defect receipt, `heartbeat_body_error`, fallback delivery) are untouched and still accurate. |
| `CHANGELOG.md` | **ADDED.** New `## Unreleased` entry, first in the list, matching the existing per-issue entry style used by #65 and #66: per-host trigger, snapshot-not-log, same-beat effect, the drop and keep lists, the three separate quota kinds, and the mechanisms deliberately not added. |
| `README.md` | No impact. Its heartbeat lines (97, 143, 210-211) state *ownership and the registration gate* — the main Skill owns project-level heartbeat, and may register a host heartbeat only after an authorized CLI allowlist exists. Both still hold exactly; this run changed the prompt's content rule, not who owns it or when it may start. |
| `docs/conventions.md` | No impact. Line 8 places project-level heartbeat policy in the generated main Skill rather than restating it; that indirection is what made this change land in one place. |
| `docs/architecture.md` | No impact. Lines 14/28/56/267 describe the main Skill's role, Agent ownership, and that a supervision heartbeat is not an execution loop. Unchanged by this run. |
| `docs/api.md` | No impact. The `heartbeat` occurrences are the `kaola-acp follow` NDJSON `kind=heartbeat` frame — a transport keep-alive, an unrelated meaning of the word. No command, flag or receipt field changed. |
| `docs/README.md` | No impact. The index lines for the Grok Bot host and the ZCode host still describe their carriers correctly; this run added no reference file and renamed none. |
| `docs/grok-bot-host.md` | No impact. Its Routine heartbeat carrier is exactly what this run preserved — Grok Bot keeps its own timer system, and no shared file or schema was imposed on it. |
| `docs/decisions/issue-7-evidence-only-interaction.md`, `docs/live-smoke-*.md`, `docs/runner-v2-dual-transport-design.md`, `docs/acp-watch/follow.md` | No impact. Dated decision records and live-smoke logs of past runs; they are historical evidence and are not rewritten. |
| Setup / install / environment | No impact. `install-local.sh`, `render-skills.py` flags, tmux/python3/CLI prerequisites and the validation commands are all unchanged. |

## Re-validation after docking

The docs commit mutates the candidate, so the prior PASS was re-earned rather than carried over:

| Check | Exit |
|---|---|
| `./scripts/render-skills.py --check` | **0** — `PASS … budgets OK` |
| `./scripts/validate.sh` | **0** — 22 suites OK, log `evidence/validate-77a9ecf.log` |

Reported to the outer coordinator as the only close-out change beyond the accepted candidate:
documentation only, no template, generated Skill, script or test byte changed.
