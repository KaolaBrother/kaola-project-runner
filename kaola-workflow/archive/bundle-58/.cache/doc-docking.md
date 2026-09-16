# Documentation docking — bundle-58 (Issue #58)

Changed public behavior checked: the ninth worker platform (Droid CLI, native ACP + PTY), default Auto Model + bypass permissions on both transports, no model/effort upgrade tier (effort only when explicitly called), the new `acp_mode_config_id` manifest key (manifest-driven ACP mode/permission option id), the `templates/budgets.json` orchestrator re-measure, and the v0.3.3 release.

- `README.md` — FIXED in 9bbf880: nine-platform counts everywhere, Droid target-table row, transport/permission/model paragraphs (default bypass both transports; no upgrade tier; effort only when called), published-evidence link for the droid live verification doc, "not a tenth platform" phrasing.
- `docs/api.md` — FIXED in 9bbf880: platform id lists + Droid, `DROID_BIN` executable override, droid ACP config ids (`model`, `reasoning_effort`, `autonomy_level`), `--permission-mode` value set (`bypassPermissions|low|medium|high|manual`), model policy.
- `docs/architecture.md` — FIXED in 9bbf880: counts → nine, droid in the platform inventory, `acp_mode_config_id` documented. Line 70 "the existing eight platforms retain byte-identical behavior" verified CORRECT (it names the eight pre-droid platforms the refactor preserved).
- `docs/conventions.md` — FIXED in 9bbf880: counts + manifest schema convention including `acp_mode_config_id`.
- `docs/runner-v2-dual-transport-design.md` — FIXED in 9bbf880: droid ACP/PTY rows with verified facts. Historical v0.3-baseline prose left unchanged deliberately (it describes the design baseline, not the current inventory).
- `docs/grok-bot-host.md` — FIXED in 1bca06b (docking fix): "not an eighth CLI worker" → "not a tenth CLI worker" (line 4). Line 19 "earlier eight-full-Markdown delivery cost" is historical cost prose and stays.
- `docs/README.md` — NO IMPACT: verified it contains no platform enumeration.
- `docs/acp-watch/README.md` — NO IMPACT: verified platform-generic (no per-platform roster).
- `hosts/grok-bot/`, `templates/grok-bot/`, `templates/orchestrator/` — NO IMPACT: scanned, no stale "eighth" phrasing; rendered reference and templates already say "tenth" (4dce730).
- `AGENTS.md` — FIXED in 9bbf880: managed-region Purpose/Architecture facts (nine AI CLI platforms, nine platform Skills, "not a tenth platform"); owner content untouched.
- `CHANGELOG.md` — FIXED in 9bbf880 + 9e6ca73: `## 0.3.3 — 2026-09-17` section with the full droid entry; empty `## Unreleased` restored on top.
- `docs/droid-live-verification-2026-09-17.md` — NEW in 6acf3ac: live ACP + PTY gate evidence (bypass evidence, resume with history, zero residue).

DOCKED
