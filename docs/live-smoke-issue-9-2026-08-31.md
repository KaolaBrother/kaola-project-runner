# Issue #9 minimal live communication proof — 2026-08-31

The candidate Skills were run directly from the Issue #9 worktree. Each platform used one exact
owned tmux session and the same minimal sequence: start, send one literal prompt, capture the
result, and force-stop only that session.

| Platform | Send/read evidence | Model evidence | Stop evidence |
| --- | --- | --- | --- |
| Grok CLI 1.0.13 | `KPR_I9_GROK_OK` read back | Grok 4.6, xhigh, Fast false | absent; relay and socket absent |
| Claude Code 2.1.246 | full prompt read back, followed by `Login expired · Please run /login` | Opus 5, high | absent; relay and socket absent |
| OpenCode 1.18.23 | `KPR_I9_OPENCODE_OK` read back | GLM 5.3 | absent; relay and socket absent |
| Kimi CLI 0.39.1 | trust choice sent through native keys; `KPR_I9_KIMI_OK` read back | K3, thinking max | absent; relay and socket absent |
| Cursor Agent 2026.08.25 | `KPR_I9_CURSOR_OK` read back | `cursor-grok-4.6-xhigh`; no Fast model selected | absent; relay and socket absent |

Claude proves command receipt only; no authenticated backend success is claimed. Catalog, model,
login, trust, and visible TUI facts remained evidence and did not block Agent-selected transport.
All five exact sessions were absent after shutdown, and no matching relay process remained.
