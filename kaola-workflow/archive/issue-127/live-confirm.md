# #127 live confirmation (2026-09-22 ~00:55, read-only, temp cwd /tmp/kpr127 since removed)

## Cursor (cursor-agent 2026.09.15-d2fe57e; manifest verified 2026.09.10-fd3934a)
- `agent --list-models`: 4.7 picker slugs are `grok-4.7-{low,medium,high,xhigh}[-fast]`, NOT `cursor-grok-4.7-*`.
  `grok-4.7-xhigh - Grok 4.7  Extra High` (display name has no "Cursor" prefix, double space);
  `-fast` names end in U+200B U+200B. `cursor-grok-4.6-*` (Cursor Grok 4.6 ...) still listed.
- ACP (`cursor-agent acp`, clientCapabilities._meta.parameterizedModelPicker=true, initialize+session/new only):
  model values grok-4.7|grok-4.6|grok-4.5 (current grok-4.6); effort low..xhigh; fast false|true.  => base `grok-4.7` MATCHES.
- Without the _meta flag the value is `grok-4.7[context=256k,reasoning_effort=high,fast=true]` (4.6 is `[effort=...,fast=...]`) — not our path.
- TUI footer NOT observed (starting the TUI risks rewriting ~/.cursor/cli-config.json model). ~/.cursor/cli-config.json
  currently holds displayName "Grok 4.6 High Fast" (no "Cursor" prefix) — footer likely lacks "Cursor"; unverified.
## Grok CLI 1.0.40 (= manifest verified)
- ACP `grok agent stdio` session/new: model values grok-4.7 (current), grok-4.7-build-fast, grok-4.6, grok-4.5; reasoning_effort xhigh current. => `grok-4.7` MATCHES.
## Side effects
- No set_config/prompt sent. CLIs rewrote their own files on startup: ~/.cursor/cli-config.json mtime 00:55:10 (model still grok-4.6),
  ~/.grok/models_cache.json, settings_cache.json. ~/.grok/config.toml untouched. No leftover processes.

## Verdict: MISMATCH → HUMAN_DECISION_REQUIRED
Expected `cursor-grok-4.7-xhigh` / footer `Cursor Grok 4.7 Extra High`; live slug is `grok-4.7-xhigh`, name `Grok 4.7  Extra High`.

## Footer probe (Host ruling Option 1; 2026-09-22 ~01:05)
Isolated config: `CURSOR_CONFIG_DIR=/tmp/kpr127h/cfg cursor-agent --trust --model <id>` in tmux, cwd /tmp/kpr127h/wd, no prompt sent.
(A temp HOME loses Keychain auth → login screen; CURSOR_CONFIG_DIR keeps auth and relocates cli-config.json.)
cursor-agent v2026.09.15-d2fe57e footers (bytes checked, plain ASCII spaces, no ZW chars):
- grok-4.7-xhigh      → `Grok 4.7 256K Extra High`
- grok-4.7-xhigh-fast → `Grok 4.7 256K Extra High Fast`
- grok-4.7-high       → `Grok 4.7 256K High`
- grok-4.7-medium     → `Grok 4.7 256K Medium`
Banner tip line reads `Try Cursor Grok 4.6 via /model` (must not be parsed as the model).
Real ~/.cursor/cli-config.json mtime/size unchanged (1790009710 / 2469) before and after; tmp dir removed; no leftover procs.
