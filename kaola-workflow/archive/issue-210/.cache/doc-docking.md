# Documentation docking — issue #210

| Surface | Result | Reason |
|---|---|---|
| README.md | no-impact | Describes the four-tier entry (Kaola-Delegator/Project Runner/Platform Runner/Workflow Next) at a level above individual Skill-prompt wording; does not quote Host-cwd guidance. Grepped for the old/new wording: no match either way. |
| docs/architecture.md | no-impact | Grepped for Host-cwd/worktree-return wording: no match. No architectural surface changed (no new files, scripts, or components — a prompt-content edit inside the existing orchestrator Skill/reference). |
| docs/conventions.md | no-impact | Grepped: no match. This issue does not touch the release/pin/operator-test conventions. |
| docs/api.md | no-impact | Grepped: no match. No ACP/CLI surface changed. |
| CHANGELOG.md | no-impact (no entry added) | Internal Skill-prompt correction (a Host operating-boundary rule promoted from a reference file into the always-loaded Skill, plus reconciling the reference's presentation), not a user-facing feature/behavior change. No `Seats: restart required/not required` operator-test path touched (`scripts/kaola-acp-holder.py`, `kaola-zcode-acp.py`, `kaola-quota.py`, `scripts/adapters`, `platforms` all untouched). Matches precedent: comparable prompt/wording-only fixes (e.g. `fix(runner): #198 ...`) landed without a dedicated changelog entry. |

DOCKED
