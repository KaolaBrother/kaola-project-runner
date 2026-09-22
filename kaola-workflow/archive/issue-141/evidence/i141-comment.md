## #141 evidence (workflow run issue-141) — main-tip real-path proof; no code change needed

**Answer to the issue's question 2:** `d2d29538` (v0.5.7) was **not** meant to contain #135 — the #135 fix landed on main *after* the v0.5.7 tag. The fix is on main; only a new accepted pin is missing.

### 1. Ancestry / yaml form (main tip `4eccf34`)
- `git merge-base --is-ancestor b279678 main` → true; #135 chain `847ca90` (fix) → `08eea7c` (test pin) → `b279678` (docs) all in main history.
- `git merge-base --is-ancestor b279678 d2d29538` → **false** (v0.5.7 predates #135).
- `platforms/cursor-cli.yaml:42` on main: `acp_effort_config_id: "reasoning_effort;effort"`; on `d2d29538`: `acp_effort_config_id: "effort"`. Generated `skills/cursor-cli-kaola-project-runner/scripts/platform.yaml:42` matches main; `render-skills.py --check` PASS.
- `CHANGELOG.md` `## 0.5.8 — Unreleased` already carries the #135 entry.

### 2. Main-tip real-path receipt (repo checkout's own Runner, not the installed d2d2953 copy)
`skills/cursor-cli-kaola-project-runner/scripts/runtime-tmux.sh start --tier default`, one disposable session `cursor-cli-KPR-i141-verify-probe`, disposable Git repo `/tmp/kpr-i141-probe` (`/tmp` itself is refused as non-Git), `KAOLA_ACP_DISPATCHER/HEARTBEAT_HOST/HEARTBEAT_HOST_SOCKET/RECORD_ROOT` unset for the call. rc 0, `state: ready`:
```json
"config_application": {
  "effort": {"advertised": true, "applied": true, "candidates": ["reasoning_effort","effort"], "config_id": "reasoning_effort", "value": "xhigh"},
  "fast":   {"applied": true, "config_id": "fast", "value": "false"},
  "model":  {"applied": true, "config_id": "model", "mapped": true, "requested_id": "grok-4.7-xhigh", "value": "grok-4.7"}
},
"effective_selection": {"effective_effort": "xhigh", "effective_model": "grok-4.7", "effort_config_id": "reasoning_effort"},
"configured_options": model=grok-4.7 (Grok 4.7), reasoning_effort=xhigh (Extra High), fast=false (Off)
```
Effort is applied **directly** through `reasoning_effort` (`applied: true`), not the v0.5.7-era indirect landing (effort apply `-32602 Unknown model config option: effort`, xhigh arriving only via the surface default). Exact stop: `stop` → `stopped: true, residual_pids: []`; `status` → `state: stopped, residual_pids: []`; holder/agent pids 40867/40868 gone.

### 3. Consumer migration off `d2d29538` (no local yaml edit)
Release side (after #140 + #141 close; `d2d29538` is an ancestor of main, so this is a forward move):
1. Content commit R′ on main (CHANGELOG `0.5.8` heading), lightweight tag `v0.5.8` at R′.
2. Pin commit P′ on `workflow/grok-bot-pin-v0.5.8`: `templates/grok-bot/accepted-revision.json` → `"stage": "pinned", "commit": "<R′ 40-hex>", "release": "v0.5.8"`, then `./scripts/render-skills.py --write` and `--check --require-pinned` (updates the pin line in `hosts/grok-bot/kaola-delegator.md`); account Skill re-saved from P′.

Consumer side (`hosts/grok-bot/INSTALL.md` §2 and §5 "Update and rollback"), per target, from the owner-selected clean checkout:
```bash
git -C "$ROOT" fetch origin --tags && git -C "$ROOT" checkout --detach v0.5.8   # R′
python3 "$ROOT/scripts/kaola-locate.py" register --target local --bin-dir "$BIN" --expect-revision <R′>
kaola-project-runner-locate --target local --expect-revision <R′>               # must be "ok"
```
(`--target cloud` for the cloud checkout.) `register` rewrites the registration receipt `$BIN/.kaola-project-runner-locate.json` (`accepted_revision` → R′); a stale receipt still naming `d2d29538` is refused as `registration-stale` until re-registered, and since R′ descends from `d2d29538` neither `accepted-revision-superseded` nor `expect-revision-superseded` fires. Installed Skill roots are refreshed by `./scripts/install-local.sh` from that checkout (v0.5.7 precedent: `--runtime codex`, `--runtime zcode`, `--skills-dir ~/.agents/skills`).

Not done in this run: no locator re-registration, no tag/release, no close/finalize/merge/push — awaiting Host acceptance.
