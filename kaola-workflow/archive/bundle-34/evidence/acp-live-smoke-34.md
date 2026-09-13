# Issue #34 ACP live smoke — 2026-09-13

Repo scratch: /tmp/kpr-34-live (git init). Commands used `scripts/kaola-acp.py` on branch
workflow/bundle-34. Raw receipts live in each session's record dir:
`$TMPDIR/kaola-501/<platform>/<session>/2567bd6b6531bf9e/{record.json,events.jsonl,holder.out.log}`
(expands to `/var/folders/j6/8368yp9j35597_g9_f148lz00000gn/T/kaola-501/...` on this machine).
Every record.json below shows `agent_alive: false` after stop — that is the exact-stop/status
proof per session; `last_prompt.mutation_status` shows the send outcome.

## Verified live (real adapters, real sessions, real send/reply/stop)

| Platform | Session | Tier/flags | Config applied (config_application) | send/reply | stop | Record dir |
|---|---|---|---|---|---|---|
| codex | acp34-default | default | model=gpt-5.6-sol, reasoning_effort=high, fast-mode=off, mode=agent-full-access | READY | stopped, residual [] | kaola-501/codex/acp34-default/2567bd6b6531bf9e |
| codex | acp34-upgrade | --tier upgrade --fast on | model=gpt-6-astra, reasoning_effort=high, fast-mode=on, mode=agent-full-access | UPGRADE | stopped, residual [] | kaola-501/codex/acp34-upgrade/2567bd6b6531bf9e |
| codex | acp34-resume | --resume 01a09b10-1716-7920-83c6-12f0fc055628 | resume-preserved: no model/effort calls; fast-mode=off, mode=agent-full-access | RESUMEDOK (turn_completed, completed) | stopped, residual [] | kaola-501/codex/acp34-resume/2567bd6b6531bf9e |
| codex | acp34-explicit | --model gpt-6-astra (bare) | model=gpt-6-astra; effort no-resolved-value (no invented effort); fast-mode=off, mode=agent-full-access | EXPLICITOK | stopped, residual [] | kaola-501/codex/acp34-explicit/2567bd6b6531bf9e |
| grok | acp34-grok | default | model=grok-4.6, reasoning_effort=xhigh; fast: no-advertised-config-option | GROKOK | stopped, residual [] | kaola-501/grok/acp34-grok/2567bd6b6531bf9e |
| opencode | acp34-oc | default | native opening model — zero model/effort/fast config calls | OCOK | stopped, residual [] | kaola-501/opencode/acp34-oc/2567bd6b6531bf9e |
| kimi-cli | acp34-kimi | default | model=kimi-code/kimi-for-coding, thinking=max, mode=yolo | KIMIOK | stopped, residual [] | kaola-501/kimi-cli/acp34-kimi/2567bd6b6531bf9e |
| kimi-cli | acp34-kimi-up | --tier upgrade | model=kimi-code/k3, thinking=max, mode=yolo | n/a (config check) | stopped | kaola-501/kimi-cli/acp34-kimi-up/2567bd6b6531bf9e |
| devin | acp34-devin | default | model=swe-2-max, mode=bypass; effort no-resolved-value; fast no-advertised-config-option | DEVINOK | stopped, residual [] | kaola-501/devin/acp34-devin/2567bd6b6531bf9e |
| cursor-cli | acp34-cursor | default (round 1, pre-mapping) | model REJECTED: -32602 "Invalid model value: cursor-grok-4.6-xhigh" → limitation; session usable | CUROK | stopped, residual [] | kaola-501/cursor-cli/acp34-cursor/2567bd6b6531bf9e |
| cursor-cli | acp34-cursor2 | default (round 2, with acp_model_map) | model=grok-4.6[effort=high,fast=true] APPLIED via map (requested_id=cursor-grok-4.6-xhigh, mapped=true, declared={effort:high,fast:true}); adapter value_name=grok-4.6 | CUROK2 | stopped, residual [] | kaola-501/cursor-cli/acp34-cursor2/2567bd6b6531bf9e |

## Cursor ACP model mapping (review round 2)

Live catalog inspection: `cursor-agent --yolo acp` `session/new` advertises `model` values as
bracketed descriptors, e.g. `grok-4.6[effort=high,fast=true]`,
`claude-fable-5-1[thinking=true,context=300k,effort=high]`. Bare IDs are rejected
(`Invalid model value: grok-4.6` verified). `platforms/cursor-cli.yaml` `acp_model_map` maps the
PTY picker IDs onto those advertised values for the same model — no semantic switch.

Honest consequence, reported not hidden: Cursor's only ACP Grok 4.6 value declares `fast=true`
intrinsically (ACP exposes no separate fast toggle and no non-fast grok value). With `--fast off`
the receipt reports `fast.effective=on`, `applied_via=model-id`, and a `conflict` note — the
descriptor is the agent's own declaration, so a false "off" is never claimed. The preset effort
xhigh is likewise not advertised over ACP (descriptor effort=high); recorded as declared evidence.

## Probes (preflight --probe, read-only)

advertised_config_ids observed: codex [mode, collaboration_mode, model, reasoning_effort,
fast-mode]; grok [model, reasoning_effort]; kimi-cli [model, thinking, mode];
cursor-cli [mode, model]; devin [mode, model]; opencode [model, effort, mode]. All match manifest
acp_*_config_id declarations. Preflight now also reports `advertised_config_options` (id, name,
type, currentValue, values) — that is the evidence surface used for the cursor mapping above.

## Known limitations

- cursor-cli ACP: Grok 4.6 is only offered as `grok-4.6[effort=high,fast=true]` — effort xhigh
  and a non-fast Grok are not advertised ACP values; reported via `declared`/`conflict`, not gated.
- claude-code ACP: not tested — owner permitted no Claude account testing on this machine.
- PTY live launches, Cloud, and Claude account flows: not tested (owner restriction); PTY paths are
  covered by static contract tests (test-model-policy.sh, test-adapters.sh) only.
- devin upgrade preset (fusion-claude-fable-5-1-high-sidekick-swe-2-medium) not live-started;
  it is the adapter's advertised current value and parses in contract-test catalogs.

---

# Corrected round — parameterized Cursor ACP (2026-09-13, second supervisor review)

The earlier "descriptor catalog" conclusion was incomplete: Cursor exposes fixed variant strings
only when the client does not negotiate `_meta.parameterizedModelPicker`. With
`clientCapabilities._meta.parameterizedModelPicker=true` at `initialize` (now sent by both the
holder `start` path and `preflight` via manifest `acp_init_meta`), Cursor ACP advertises separate
native `model` / `effort` / `fast` config options — base model IDs, `low|medium|high|xhigh`, and
`"true"`/`"false"` strings. The incorrect `grok-4.6[effort=high,fast=true]` mapping is removed;
picker IDs now decompose (`acp_model_map` → base ID, ID suffix → effort option, `--fast` → fast
option via `acp_fast_values off=false,on=true`). Fable upgrade inspected on the same parameterized
surface: `claude-fable-5-1` is an advertised model value; the session-level `effort`/`fast`
options apply to it identically, so `claude-fable-5-1-high` maps to `claude-fable-5-1` + `high` +
`false`.

## cursor-cli — acp34-param-cursor (record dir kaola-501/cursor-cli/acp34-param-cursor/2567bd6b6531bf9e)

- `preflight`: `advertised_config_options` ids `[mode, model, effort, fast]`; model current
  `grok-4.6`; effort values `[low, medium, high, xhigh]`; fast values `[false, true]` — proves the
  production `--init-meta` wiring negotiates the parameterized picker.
- `start` (default tier): `config_application` applied in order —
  `model=grok-4.6` (`requested_id=cursor-grok-4.6-xhigh`, `mapped=true`), `effort=xhigh`,
  `fast="false"` (string). `fast.effective=off`, `applied_via=acp-config`. All three applied
  before any prompt.
- `send` "Reply with exactly the token VERIFIED_XHIGH_OFF and nothing else": `turn_completed`,
  `stop_reason=end_turn`; capture `final_text="VERIFIED_XHIGH_OFF"`, zero tool events.
- `stop`: record `state=stopped`, `agent_alive=false`, `residual_pids=[]`; a post-stop
  `ps` scan for the session name found no processes.
- Raw records: `{record.json,events.jsonl,holder.out.log,holder.sock}` under the record dir.

## Cleanup audit (this round)

- Killed exactly 114 owned test holder+mock process pairs from the validate run — identified by
  `--record-dir` under `kaola-acp-contract-*` / `kaola-acp-watch-*` temp roots and their direct
  child PIDs; zero remain. No pattern kill touched any other session.
- Verified: 0 processes under `.kw/worktrees/bundle-34`; foreign sessions preserved — main-checkout
  `devin-kaola-project-runner`/`scripts/kaola-acp-holder.py` holders and tmux `kaola-9362e3d5` /
  `kaola-fb9f6f4c` untouched.
