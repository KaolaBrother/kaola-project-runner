# Documentation docking — Issue #97 (candidate c675835)

Checked against AGENTS.md's documentation map (README, CHANGELOG, docs/) for the changed public
behavior: the Codex installer destination now installs a user-level `SessionStart(compact)`
recovery entry; `scripts/kaola-codex-compact-hook.py` gains `user-install`, `user-uninstall`,
`user-status` (with `install_blockers`), `user-emit`, and `--codex-home`.

| File | Result |
|---|---|
| `docs/codex-host.md` | rewritten: user-level entry (default), project-level entry (legacy, unchanged), coexistence/migration predicate, trust/new-session caveats, live boundary on codex-cli 0.153.4/0.155.1 |
| `docs/api.md` (Installer) | paragraph added: Codex destination hook install/uninstall scope, `--skills-dir` boundary, planning-time refusal, direct actions |
| `README.md` | installer section paragraph + hook pointer under "Agents that load the Skills" |
| `docs/README.md` | Codex Host index line updated |
| `CHANGELOG.md` | `## Unreleased` entry (renamed to 0.5.0 at release) |
| `scripts/install-local.sh --help` | usage text describes the hook, its scope, and the trust note |
| `AGENTS.md` | no impact: install/test/build commands unchanged; project facts unchanged |
| `docs/architecture.md`, `docs/conventions.md` | no impact: no new generated surface, no template or budget change; `skills/` and `hosts/` unrendered (render-skills --check PASS) |
| Skill templates (`templates/orchestrator`, `templates/kaola-delegator`) | no impact: the hook is the carrier; Skill text unchanged, budgets untouched |
| `docs/zcode-host.md`, `docs/grok-bot-host.md` | no impact: other hosts out of scope (stated in codex-host.md) |

Evidence path named in `docs/codex-host.md`
(`kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/`) is the post-archive
location of `kaola-workflow/issue-97/evidence/codex-user-compact-live/`, matching the #75
convention.

DOCKED
