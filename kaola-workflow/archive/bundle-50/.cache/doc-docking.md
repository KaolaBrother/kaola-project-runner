# Documentation docking — bundle-50 (Issue #50), candidate 8095611

Checklist from AGENTS.md (README, CHANGELOG, docs/) against changed public behavior: the Claude Code
worker's ACP transport (vendored bridge, Skill-relative `acp_command`, exact-binary env, new
`bridge`/`runtime_binary` receipt facts, `acp-bridge-missing` refusal, default transport `acp`,
supply-chain rule, subscription/Settings boundary, bridge state file), manifest fields, validation
suite additions, and the superseded wrapper decision.

| Surface | Checked | Result |
|---|---|---|
| `README.md` | transport table row (ACP), transport paragraph: vendored fork, upstream pin, exact binary, subscription/Settings boundary, no registry/npx, PTY fallback + login, bridge state file | docked (commits 4a1ea1f, 8a6ddac, 46c7492) |
| `docs/api.md` | manifest transport fields; `$SKILL_DIR/scripts/` token resolution and layouts; `bridge`/`runtime_binary` receipt facts; `acp-bridge-missing`; `CLAUDE_ACP_CLAUDE_BIN`; vendored files shipped; `CLAUDE_ACP_STATE_DIR`/`CLAUDE_ACP_RUNTIME_DIR` | docked; field names transcribed from `scripts/kaola-acp.py` (`resolve_agent_command`, `bridge_facts`) and `vendor/claude-code-acp/src/config.ts` |
| `docs/architecture.md` | component diagram: Claude Code path through the vendored bridge | docked |
| `docs/runner-v2-dual-transport-design.md` | v0.3 item 1 annotated; v0.4 decision block (bridge, supply chain, Settings boundary, options, default flip + rollback) placed after the v0.3 list | docked (review F2 fixed) |
| `CHANGELOG.md` | Unreleased entry for Issue #50 Missions 1–4 above #49's R3 entry | docked (review N4 fixed) |
| `platforms/claude-code.yaml` → generated `skills/claude-code-kaola-project-runner/SKILL.md`, `references/acp.md`, `references/platform.md` | ACP command, quirks, login-PTY, default transport, launch summary rendered from the manifest | docked by `render-skills.py --check` PASS |
| `vendor/claude-code-acp/UPSTREAM.md` | upstream URL/commit/MIT, complete modification list (items 1–9 incl. Mission 3/4 fork changes), hashed inventory | docked; enforced by `test-issue-50-claude-acp-bridge.py::test_provenance` |
| `AGENTS.md` | project facts (purpose, commands, constraints) — no new command or constraint; `vendor/` is source, `skills/` remains generated output | no impact |
| Examples / setup / environment | installer unchanged (copytree carries `scripts/vendor/`); env variables documented in docs/api.md and README; no new setup step | no impact beyond the docked files |
| `docs/acp-live-verification-2026-09-11.md` | historical wrapper probe record | intentionally unchanged (history) |

No invented fields: every documented key exists in the code or manifest at 8095611. Registry-name
guard (`npx claude-code-acp`, `npm install -g claude-code-acp`) passes across README, docs,
platforms, scripts (harness `test_provenance`).

Status: DOCKED
