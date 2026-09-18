# Documentation docking — Issue #70

Candidate under docking: `bf9fda3` (rebased onto main 3dd7e5e); docs committed on top.

| Surface | Checked | Outcome |
|---|---|---|
| `README.md` | yes | No impact — it introduces the Skills and install flow, and states no ACP receipt fields or Host beat procedure. |
| `CHANGELOG.md` | yes | **Fixed** — new `## Unreleased` entry stating the reported binding fact (`heartbeat_host`, `heartbeat_host_known`, `heartbeat_host_requested`), that unbound workers stay legal, the internal missed-binding recovery with the bounded `wait`, the exception-only outward report, and the native-id sourcing rule. |
| `docs/api.md` | yes | **Fixed** — the Observation schema section now records the three ACP receipt fields, the `no-session` silence, and the `session-exists` answer. |
| `docs/zcode-host.md` | yes | **Fixed earlier in the run** (commits d6ba1df…bda182a): binding fact, internal recovery, and the `native_session_identity` source of the native resume id. |
| `docs/architecture.md` | yes | No impact — component-level architecture; no receipt field list and no Host beat detail. |
| `docs/conventions.md`, `docs/decisions/` | yes | No impact — no convention or decision record changed; the Issue's rules live in the generated Skill and its references. |
| `AGENTS.md` | yes | No impact — project facts, commands and constraints are unchanged (no new command, no new validation policy, no new generated surface). |
| Generated Skill surface (`skills/kaola-project-runner/`) | yes | **Fixed by the renderer** from `templates/orchestrator/` — `SKILL.md` untouched, `references/zcode-host-dispatch.md` and `references/host-startup.md` carry the new rules; budgets unchanged (8180 B / 7479 B of 8192 B). |
| Setup/environment/examples | yes | No impact — no new binary, environment variable, or install step; `KAOLA_ACP_HEARTBEAT_HOST` already existed. |

Transcribed from the real artefacts, not invented: field names and behaviour were taken from
`scripts/kaola-acp.py` (`attach_binding_fact`, `heartbeat_host_requested`) and
`scripts/kaola-acp-holder.py` (`write_record`/`op_state`), and the native-id rule from the
measured probe in `evidence/native-id/findings.md`.

Status: DOCKED
