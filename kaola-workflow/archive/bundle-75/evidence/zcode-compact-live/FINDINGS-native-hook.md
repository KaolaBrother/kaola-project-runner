# ZCode native-hook compaction recovery — live findings (round 2)

Scope: bounded isolated experiment on installed ZCode 3.12.3 / CLI 0.16.5, per outer review:
empirically test whether a native `UserPromptSubmit` plugin hook (a) fires on the installed
runtime, (b) can detect a real compaction from existing persistent records with no new ledger,
and (c) injects a recovery carrier that actually reaches the model's next reasoning.
Distinguish manual `/compact`, programmatic `session/compact`, and runtime auto compaction.

## Isolated fixture

- Scratch git repo `/tmp/kpr-i75-native/repo`; planted `.kpr/skills/kaola-project-runner/SKILL.md`
  carrying reload marker `KPR-SKILL-RELOAD-8842`.
- Project-scoped `.zcode/config.json`: `{"plugins":{"dirs":["/tmp/kpr-i75-native/plugin"]}}`.
  Plugin roots listed in `plugins.dirs` load with `defaultEnabled`; their hooks dispatch with
  `sourceKind:"plugin"` and bypass workspace trust admission — **zero writes to the user-global
  `~/.zcode/cli/config.json` (`hooks:{}` verified unchanged throughout)**.
- Plugin root: `.zcode-plugin/plugin.json` + `hooks/hooks.json`
  `{UserPromptSubmit:[{hooks:[{type:"command",command:".../hook.sh"}]}]}`.
- `hook.py` per invocation: parses stdin JSON (`session_id`, `hook_event_name`, `prompt`,
  `transcript_path`); queries the existing `part` table read-only for the newest
  `context_compaction`/`compaction` row of that session; compares `time_created` against a
  hook-private cursor file under `$ZCODE_PLUGIN_DATA`; emits
  `{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":<carrier>}}`
  exactly once per newly observed compaction episode.
- No send-path gate, no polling loop, no scheduler, no second ledger. Credentials never copied,
  decrypted, or logged — the driver reuses the adapter's in-memory
  `interaction/requestProviderRuntimeHeaders` answer.

## Results

| Leg | Verdict |
|---|---|
| L0 — benign prompt, no compaction | **PROVEN**: hook fired, `inject:false`, model answered `PING-OK` |
| LM — typed `/compact` then probe (`sess_194d7421`) | **PROVEN end-to-end**: part rows `trigger:"manual"` / `phase:"standalone_turn"` / `ts=1789755145907`; next prompt `inject:true`; model issued a real `read` on the planted SKILL.md and quoted `KPR-SKILL-RELOAD-8842`. `/compact` itself bypasses `UserPromptSubmit` (slash commands skip the hook — no spurious injection). Following prompt `inject:false` — once-per-episode cursor works. |
| LR — programmatic `session/compact` RPC (`sess_25e3d20d`) | **PROVEN end-to-end**: direct `app-server --stdio` driver (adapter's own backend class + auth helpers) sent `session/compact` → `compact_started` → `operationId compact_c3390f77` → summarization call → `turn.completed`; part rows identical in shape (`trigger:"manual"`, `compactReason:"user_requested"`); next prompt `inject:true` → model quoted the marker. This is a mid-run programmatic trigger — not prompt-typed `/compact`. |
| LA — runtime auto compaction (`trigger:"auto"`) | **UNTRIGGERED at bounded cost**: 8 sequential ~34k-token file reads drove GLM-5.3 input to **494,040** tokens with zero compaction parts. Live `session.updated` reported **`contextWindow: 1,000,000`** — the auto threshold sits near ~966k+; crossing needs ~8M provider tokens. GLM-5.3-Flash (also 1M window per vendor spec) absorbed **288,926** tokens with zero compaction. |
| Mid-turn auto (`phase` ≠ `standalone_turn`) | **UNTRIGGERED**: same threshold wall; compactions are inter-turn by design (`Cannot compact while a prompt is running`). |

## Coverage statement

- Detection is **trigger-agnostic**: the hook reads `part` rows regardless of `trigger`/`auto`
  values; the values are only logged. Static analysis: manual and auto compaction write through
  the same `context_compaction` record path into the same table and schema.
- **Proven carriers**: typed `/compact` and programmatic `session/compact` RPC — the latter is
  mid-run coverage in the channel sense (compaction not authored as prompt text).
- **Residual**: a `trigger:"auto"` record was not observed live. Coverage extends to auto by
  construction (identical schema + trigger-agnostic read), but that is inference, not an
  observed proof. On the installed provider the only catalog models are 1M-window; a real
  `trigger:"auto"` leg requires ~8M provider tokens — outside bounded scope.

## Proposed minimal boundary (for outer review — not shipped in this candidate)

- Deploy-time: the consuming repo gets a project-scoped `.zcode/config.json` `plugins.dirs`
  entry plus a plugin dir (`hooks/hooks.json` + hook script). No user-global config writes,
  no credential material, no workspace-trust dependency.
- Run-time: hook is stateless per prompt — one read-only `MAX(time_created)` `part` query plus
  a cursor file under `$ZCODE_PLUGIN_DATA`. No Runner send gate, no cursor ledger owned by
  transport, no heartbeat.
- Reachability gap: `session/compact` is **not** exposed through the adapter's fixed method
  dispatch, so the Runner cannot currently invoke a programmatic mid-run compact through
  `kaola-tmux`. Surfacing it would need one narrow adapter op — proposal only.

## Evidence files

- `hook-invocations.jsonl` — 7 `UserPromptSubmit` invocations across 3 sessions; inject flags,
  compaction timestamps, trigger/phase fields.
- `rpc-compact-events.jsonl` — 120-event sanitized trace of the `session/compact` run
  (compact lifecycle, `contextWindow: 1000000`, marker response). No credential material.
- `db-compaction-parts.json`, `events.jsonl`, `FINDINGS.md` — round-1 ACP `/compact` leg.

## Stop evidence

`kpr-i75-zcode` and `kpr-i75-flash` stopped via `kaola-tmux.sh zcode stop` —
`stopped:true`, `residual_pids:[]`, scratch repo `dirty:false`. No user config, credential,
or session of any other owner touched.
