# Issue #69 — bounded live diagnosis (2026-09-18)

Candidate SHA: `3dd7e5eb5c4efe679ffbf4717307bf74866e5463` (`workflow/bundle-69`, clean).
Adapter under test: `kaola-zcode-acp` v0.3.0 (blob `6b20120`), holder `55e5c10`.
Runtime: ZCode desktop 3.12.3 / CLI bundle 0.16.5
(`/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs`,
node `/opt/homebrew/Cellar/node@24/24.18.0/bin/node`).

## Verdict

**All three requested legs are UNPROVABLE live on this install right now.** The
local ZCode runtime cannot materialize any usable session through the real
adapter — two independent walls, both reproduced through the real
holder+adapter stack and at the raw wire level. Nothing was faked; the
blockers below are themselves the live evidence. No production code changed.

## Wall 1 — app-server exits at spawn (reproduced the reported symptom)

`node glm/zcode.cjs app-server --stdio` dies in ~0.6 s (exit 1) before any
request is served. Stderr (adapter discards it; captured directly):

```
无法定位 CLI ZCode Built-in Provider Config：
/Applications/ZCode.app/Contents/Resources/glm/provider/zcode-builtin.json,
/config/provider/zcode-builtin.json
```

Root cause: `resolveNodeProviderRuntimePaths` (`qSo`) resolves the builtin
provider config relative to the entry path. Neither candidate exists; the real
file lives at `Resources/config/provider/zcode-builtin.json` (one level up from
`glm/`, not the five the resolver assumes). The runtime's own bypass —
`ZCODE_BUILTIN_PROVIDER_CONFIG_FILE` + `ZCODE_PERSONAL_PROVIDER_CONFIG_FILE`,
or `--prepare-storage` — keeps it alive, but the adapter's child-env allowlist
(`ENV_ALLOWLIST`, 12 names) strips both vars and offers no flag slot, so via
the stock adapter+entry the spawn always dies.

Real-stack receipt: `01-host-start.json` — `zcode app-server exited` inside
`config-option-failed` (holder `4532ee51967f93209717964968d13a31`, holder_pid
17381, agent_pid 17397). Wire-level: `10-probe-spawn-crash.txt`.

## Wall 2 — `runtimeModel` is dead protocol on 0.16.5

With a project-local entry shim (env surface `KAOLA_ZCODE_ENTRY` — the one
allowlisted name — pointing at a wrapper that sets the two bypass vars then
requires the real bundle; `entry-shim/zcode-entry.cjs`, probe-only), the
app-server stays up and the REAL adapter reached `session/create`. Real
receipt `03-host-start-shim.json`:

```
zcode error for session/create: ZodError — Unrecognized key: "runtimeModel"
```

`runtimeModel` occurs **zero times** in the 0.16.5 bundle — the adapter's
provider-injection on create/resume/setModel is gone from the wire schema.
Adapter v0.3.0 sends it unconditionally (no retry — the retry lives only in
Issue #74's unmerged commit `a23f9f5`), so `materialize()` cannot create any
session. The resume path fails differently but just as surely (setModel wants
`model` as `"providerId/modelId"` string; `reregister_provider` raises).

Raw wire evidence (`11-probe-model-and-turn.txt`, env-bypassed app-server):

- `session/create` + `runtimeModel` → `ZodError unrecognized_keys`.
- bare `session/create` → `sess_8fb5a8e6` created, but `model.available: []`
  (empty provider registry — personal `provider_config.json` has zero rules).
- `session/send` → turn accepted, then **real `turn-failed`**:
  `CONFIGURATION_ERROR: "Select a model before continuing"` — identical to the
  wall Issue #74 documented at ~20:00.
- `model` object in create → `Provider Registry 中不存在 Model`;
  `setModel` with object → stringified `[object Object]` miss.

## Leg disposition

| Leg | Live status | Offline coverage |
|-----|-------------|------------------|
| Real `turn_failed` staged→delivered→confirmed | **Unproven** — no session can materialize; a real turn never starts under the holder | `test-zcode-heartbeat-contract.py` (`on_prompt_response`→`turn_failed`→idle event reason `outcome=turn_failed`) |
| Resume redelivery of unconfirmed event | **Unproven** — same blocker; `--resume` also dies (setModel/registry) | `test_resume_redelivers_unconfirmed_events` (fake server) |
| Duplicate-event dedup | **Unproven** — events can stage on a live host socket but can never be delivered/confirmed without a working turn | `test_bounded_queue_dedup_and_single_batch_flush` |

Note: dedup *acceptance* (duplicate→`duplicate:true`, no second staged event)
is holder-socket logic and could run against a live host holder — but it is
only meaningful with a real agent behind it, and the honest reading of the
issue is end-to-end staging→delivery semantics, which need a working turn.

## Timeline context (why it worked this morning)

Issue #70 ran REAL ZCode turns at 17:12–18:36 today through the identical
adapter+bundle (`cli=0.16.5` on their receipts). At 19:08 the desktop app
relaunched: `~/.zcode/v2/provider_config.json` was rewritten to empty rules,
`~/.zcode/v2/runtime/provider/...` was downloaded, `zcode-cli` (SEA binary,
PID 10078) started. Since then every headless create hits wall 2 — i74 at
~20:00, this probe at ~20:45. Whatever populated the headless provider
registry before 19:08 (most plausibly a non-empty `provider_config.json` or a
different resolution path) is gone. `sess_9a709c7e`, still doing work at
20:40, is the DESKTOP session hosted by `zcode-cli` — a different process
tree, not the headless `node glm/zcode.cjs` path the adapter uses.

## Defect characterization (for the outer reviewer, not fixed here)

The installed ZCode 3.12.3/0.16.5 removed the `runtimeModel` overlay the
adapter depends on, and the adapter additionally cannot spawn the app-server
because of the provider-config path bug. Issue #74 hit the same two walls;
their adapter-side create-retry (`a23f9f5`) is on their branch only and still
cannot yield a working model (empty registry → "Select a model"). A full fix
is #74-class work — out of scope for #69, which asked for evidence, not a
protocol migration. Fixing it here would also still require authoring the
proprietary personal-provider-rules file to populate the registry.

## Evidence inventory (`evidence/`)

- `01-host-start.json` / `01-host-start.err` — real-stack wall-1 receipt
  (holder `4532ee51967f93209717964968d13a31`, ACP `zcode-1`, pids 17381/17397).
- `02-host-stop-wall1.json` — exact stop, `residual_pids: []`.
- `03-host-start-shim.json` — real-stack wall-2 receipt: ZodError
  `runtimeModel` on `session/create` (holder `c85fa04d317db351655a2c8f141ab044`,
  pids 79542/79543).
- `04-host-stop-shim.json` — exact stop, `residual_pids: []`.
- `10-probe-spawn-crash.txt` — wire-level spawn crash + provider-config stderr.
- `11-probe-model-and-turn.txt` — raw wire: create variants, real session
  `sess_8fb5a8e6`, real `turn-failed`/`Select a model`.
- `probe-*.py` — the probe scripts themselves (read-only credential use:
  desktop registry read in-process, sent only inside the wire overlay in
  earlier variants; never logged).

Orphan note: bare-probe creates left three empty native sessions in
`~/.zcode/cli/db` (`sess_e1fdb198`, `sess_b1053ed0`, `sess_8fb5a8e6`) — zero
real turns completed (the two sends failed pre-model). Left in place; deleting
them via `session/close` was not attempted to avoid touching shared CLI db
state beyond what the probes already did.

Nothing global was modified: no `~/.zcode` config/credentials written, no
other Runner session/worktree touched, no tmux sessions used. All stops are
exact with `residual_pids: []`.
