# Documentation docking — issue #164

Candidate: `89fc21bd780216e8e7a850729c7472c95fb5a547`

Checked:

- `CHANGELOG.md` — Unreleased bullet for #164 states the shared presence decision, the pre-spawn fact set (`bridge` / `runtime_binary`, version only when the runtime binary is already an absolute executable), and the unchanged refusal fields (`mutation_status` `not_started`, `mutation_performed` false, drain-restart `action` and `start_selection`). The existing Unreleased seats line stays on the #162 holder change. This bullet does not change the holder, the ZCode bridge, or the ACP protocol. No edit.
- `docs/api.md` — already says `kaola-acp.py` reports `bridge` (`relative`, `path`, `layout`, `present`, `sha256`, `upstream_pin`, `verified_versions`) on preflight and start, and that a token resolving to no file is `acp-bridge-missing` with nothing spawned. It already says preflight and start fail closed without explicit `KAOLA_ZCODE_ENTRY` and `KAOLA_ZCODE_NODE`. The refusal path now returns that same preflight fact set; success-path start still attaches `bridge_facts` without a version probe, which is what the "on preflight the `--version` line" clause describes. No edit.
- `docs/conventions.md` — release-note and validation rules are unchanged. No edit.
- `README.md` — does not document these receipt fields; the command surface stays in `docs/api.md`. No edit.
- `AGENTS.md` — documentation map and release bullet are unchanged. No edit.

DOCKED
