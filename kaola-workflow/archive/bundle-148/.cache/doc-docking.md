# Doc docking — bundle-148 (Issue #148, quota packages + model-package + ACP quotaPool stamps)

Checked against AGENTS.md documentation map and the branch's changed public behavior
(tip ace35ab, base d62ab08):

| Surface | Status | Reason |
|---|---|---|
| docs/api.md | covered by branch (a8173a6) | `kaola-acp packages` / `model-package` schemas, stamp emission contract, unmapped rule, examples — full contract text verified by Host |
| README.md | covered by branch (a8173a6) | read-only query surface named next to the #147 survey text (usage lane entry) |
| skills/kaola-project-runner/references/quota-packages.md + orchestrator SKILL.md | covered by branch | Project Runner reference named from docs/api.md; main-skill-build.json bumped with the new reference (byte budgets respected, render --check PASS) |
| platform skill references/acp.md (10 platforms) | covered by branch | one-line quota pointer per platform copy, generated from templates/references/acp.md.tmpl |
| CHANGELOG.md | no-impact this run, deferred | version-headed changelog (top: 0.5.9); Owner ruling for this run: no version bump, no release cut. Entry owned by the next release cut (v0.6 intent recorded in run records) |
| AGENTS.md / docs architecture | no-impact | no architecture or command-surface change beyond the documented query contract; install/test commands unchanged |

DOCKED
