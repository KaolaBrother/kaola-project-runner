# Doc docking — bundle-62 (issue #62)

Checked against the AGENTS.md Documentation Map and this run's changed public behavior:
`--runtime zcode` install path, generic external-ACP ZCode Host entry (three session
identities), nested Host→Worker isolation, event-driven heartbeat carrier
(`KAOLA_ACP_HEARTBEAT_HOST`, full prompt body per event, turn-boundary delivery).

- `README.md` — ZCode runtime install documented (`--runtime zcode` → `~/.zcode/skills`;
  workspace `.zcode/skills` via `--skills-dir`), lines 104 and 248-250; 19 zcode mentions.
  No fix needed.
- `docs/api.md` — 13 zcode mentions covering the host/worker entry surface. No fix needed.
- `docs/architecture.md` — 7 zcode mentions covering the new host role and carrier. No fix
  needed.
- `CHANGELOG.md` — 38 zcode mentions; includes the `KAOLA_ACP_HEARTBEAT_HOST` event-driven
  carrier entry. No fix needed.
- `docs/zcode-host.md` — dedicated doc covering: the two faces of ZCode, the generic ACP
  entry, session identity, nested Host→Worker isolation (contract), the unchanged
  credential/config boundary, Phase 2 event-driven heartbeat, and verification (37
  mentions; section map checked). No fix needed.
- The Phase 2 orchestrator audit (2026-09-17) verified the zcode-host.md Phase 2 section
  and the CHANGELOG entry match the implementation line-for-line.

DOCKED
