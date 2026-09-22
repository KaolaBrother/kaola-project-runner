# Issue #135 — cursor-cli ACP effort config id: fix design (design-only run)

Run: `kaola-workflow/issue-135`, branch `workflow/issue-135` (no source change in this run).
Base: main `d2d2953` (v0.5.7). Live CLI: `cursor-agent 2026.09.18-9a7762b`, Skill build `dec23a787644`
(`~/.agents/skills/cursor-cli-kaola-project-runner`, byte-identical to `skills/cursor-cli-kaola-project-runner`).
Date: 2026-09-22. Author: worker `claude-code-KPR-i135-fable-design`.

## 1. Gap (restated with citations)

- `platforms/cursor-cli.yaml:33` `acp_effort_config_id: "effort"`; `:35` `acp_quirks` describes a single
  `effort low..xhigh` option; `:36` `acp_verified_versions: "cli=2026.09.15-d2fe57e;protocol=1"`.
- `scripts/kaola-acp.py:2723-2748` sends `("effort", effort_value, "acp_effort_config_id")` with the manifest id
  literally; a rejection becomes `config_application.effort.applied:false` and the run proceeds (honest, degraded).
- `scripts/kaola-acp.py:2091-2104` `effective_selection` reads the agent's `currentValue` by the same manifest id,
  so `effective_effort` is `null` instead of the real value.
- Reproduced live (probe-1): default tier → model `grok-4.7` applied (mapped from `grok-4.7-xhigh`), `fast=false`
  applied, effort `-32602 "Unknown model config option: effort"`, `effective_selection.effective_effort: null`.

## 2. Live verification (mission 1) — the open fact and what it actually turned out to be

All sessions were started with the installed v0.5.7 Skill at the canonical root and exact-stopped (`stopped: true`,
zero residue). No prompt was sent; no `/model` probe. The two leaked Host variables
`KAOLA_ACP_HEARTBEAT_HOST`/`_SOCKET` had to be unset (known leak; first start refused `heartbeat-host-conflict`).

```bash
SKILL_DIR=~/.agents/skills/cursor-cli-kaola-project-runner
REPO=/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner
env -u KAOLA_ACP_HEARTBEAT_HOST -u KAOLA_ACP_HEARTBEAT_HOST_SOCKET \
  "$SKILL_DIR/scripts/runtime-tmux.sh" start --repo "$REPO" --session cursor-cli-kaola-i135-effort-probe
# then over the holder socket (kaola-acp.socket_request): set_config_option / state
"$SKILL_DIR/scripts/runtime-tmux.sh" stop  --repo "$REPO" --session cursor-cli-kaola-i135-effort-probe
```

**Answer to the open fact: YES.** On a plain `cursor-agent --yolo acp` launch, after `model=grok-4.7` is applied
through the config option, `set_config_option reasoning_effort=xhigh` answers `configured:true`,
`option_name "Effort"`, `value_name "Extra High"`, and `state` then advertises `reasoning_effort=xhigh`
(probe-5 steps C4→C7; probe-3/4 on the first session). Direction 1 needs no launch-arg support.

**The larger fact (changes the design):** the effort option id is a property of the *selected model's* parameter
schema, not of the CLI version. Measured on one live session by switching `model` and reading the advertised
`configOptions` (probe-5, probe-9):

| model value | advertised options after the model apply (id · category · current) | effort id | rejected id |
|---|---|---|---|
| `grok-4.7` | mode · model · `context`(model_config, 256k) · `reasoning_effort`(thought_level, xhigh) · fast | `reasoning_effort` | `effort` -32602 |
| `grok-4.6` | mode · model · `effort`(thought_level) · fast | `effort` | `reasoning_effort` -32602 |
| `claude-fable-5-1` | mode · model · `thinking`(thought_level, true) · `context`(model_config, 300k) · `effort`(thought_level, high) | `effort` | `reasoning_effort` -32602 |
| `gpt-5.6-sol` | mode · model · `context`(272k) · `reasoning`(thought_level, medium) · fast | `reasoning` | — |

So a single flipped id (`reasoning_effort`) fixes the default tier and **breaks the upgrade tier** (Claude Fable 5.1
uses `effort`). Name `"Effort"` is shared by grok-4.7/grok-4.6/fable but not gpt; category `thought_level` is shared
but Fable carries two such options (`thinking`, `effort`). Neither name nor category is a safe selector.

Secondary fact: the CLI persists the selected model and its parameters in `~/.cursor/cli-config.json`
(`selectedModel`, `modelParameters` keyed by model, `modelSelectionHistory`); a plain launch advertises the
persisted model's schema, and every `session/set_config_option` re-persists it. That is why the issue's plain launch
showed `grok-4.6` + `effort=high` and why this Mac's plain launch now shows `grok-4.7` + `reasoning_effort=xhigh`.
The Runner start already applies model first, so it never depends on that persisted state — but the *effort id* it
sends must follow the model it just applied.

Evidence files (`kaola-workflow/issue-135/evidence/`, sha256):

| file | what | sha256 |
|---|---|---|
| probe-1-start.json | v0.5.7 default-tier start receipt (regression reproduced) | 59011079dd35752c585cb4dbc335af505cb9846055933931df104943db5d3be6 |
| probe-2-status-before.json | status incl. `initial_config_options` | e9cb5ec8954ce22bf157dc310a1e4095474b845dbf9acaf2a2fcf183cc093bc7 |
| probe-3-set-reasoning-effort-xhigh.json | the open-fact set: configured true, "Extra High" | 3a6a74950cfb75c2ccd8c2e85710a486f1109ecb395124c2ada96b06cb47eac6 |
| probe-4-state-after.json | state after the set | a9244fa9b11fd9f085c0c22183cdd8d941672e05d61653a39ca8f931743af3bb |
| probe-5-schema-experiment.json | C1–C13 per-model id switching, every reply | 7d5b1cbeca9b67577f57677846da6156c2b5e2bcf34727fd896709050a72ecc8 |
| probe-6-final-config-options.json | full grok-4.7 option payload with choices | 1a56b2bbd915d271d6d7cd80a157c9592da833efd2f1e3eea0e0f6980b466699 |
| probe-7-stop.json | exact stop, `stopped: true` | 81fafff3b394450ff5ee2519089285777c05914c170fdefeccbe0ca822759e67 |
| probe-8-start2.json | second session start | 006fcbde120e21f5ba6db86785258177b1a886aa07b6ebf475f7e275ef493222 |
| probe-9-option-categories.json | full option payloads for grok-4.7 / fable / grok-4.6 / gpt-5.6-sol | 2ffd134018668b7d0695bd30e893ae4a88c6cb0d0d2e831b0e5364e1d63070c4 |
| probe-10-stop2.json | exact stop, `stopped: true` | 1086f676564dd166bf6034ed4d83f1eb0670ab0dd79a9f6333114abdeb94fe4e |

## 3. Chosen direction

**Direction 1′ — manifest candidate list resolved against the agent's own advertised options.**

- `acp_effort_config_id` becomes an ordered `;`-separated candidate list (a single id is a one-element list, so
  every other manifest is unchanged). Cursor declares `"reasoning_effort;effort"`.
- After the model option is applied, the driver reads the holder `state` once and sends effort through the **first
  candidate the agent advertises**. If no candidate is advertised (or the agent advertises nothing), it sends the
  first candidate literally — exactly today's behavior and today's limitation receipt.
- `effective_selection` reads `effective_effort` through the same resolution.

Why this and not the others:

- Direction 1 as written (flip to `reasoning_effort`) fixes default and silently breaks `--tier upgrade`
  (measured: Fable uses `effort`). A per-model static map (`grok-4.7=reasoning_effort;claude-fable-5-1=effort`)
  would work today but encodes exactly the kind of schema fact this issue shows drifting per model/version.
- Direction 2 (launch `--model grok-4.7-xhigh acp`) is not needed (the option is settable after a plain launch), needs
  a per-platform launch-arg mechanism in the holder, only covers models with a full catalog slug, and its launch-time
  selection is persisted into the user's `cli-config.json` — a bigger surface for no gain.
- Direction 3 adds the launch flag "as primary" plus the option "as fallback": two mechanisms for one fact.
- Reading the advertised list is the same category of evidence the receipt already uses (`effective_selection`,
  `advertised_config_options`); it is not a gate, classifier, retry, or wait — the session stays usable on rejection.

## 4. Manifest (`platforms/cursor-cli.yaml`)

```yaml
acp_quirks: "agentInfo is empty; initialize with _meta.parameterizedModelPicker=true so ACP advertises separate model/effort/fast options with base model IDs and string true/false fast values; the option SET follows the selected model (grok-4.7: context + reasoning_effort; grok-4.6 and claude-fable-5-1: effort; fable also thinking), so the effort id is resolved from the options advertised after the model apply; the CLI persists the selected model and parameters in ~/.cursor/cli-config.json and a plain launch advertises that persisted schema"
acp_verified_versions: "cli=2026.09.18-9a7762b;protocol=1"
acp_effort_config_id: "reasoning_effort;effort"
```

Unchanged: `default_model_*` (`grok-4.7-xhigh`, effort xhigh, fast false), `upgrade_model_*`
(`claude-fable-5-1-high`, effort high), `acp_model_map`, `acp_fast_*`, `acp_init_meta`, `acp_command`.
`default_model_parameters` wording "effort=xhigh (encoded in model ID), fast=false" stays true.

## 5. Driver (`scripts/kaola-acp.py`)

1. New helper next to `parse_manifest_value_map` (≈ line 1640):
   ```python
   def parse_config_id_candidates(raw: str) -> list[str]   # "a;b" -> ["a","b"], "" -> []
   def resolve_config_id(candidates, state) -> tuple[str, bool]
       # first candidate whose id appears in state.session_meta.configOptions -> (id, True)
       # none advertised / no options -> (candidates[0], False); no candidates -> ("", False)
   ```
2. Apply loop (`:2723-2748`): keep model first. After the model set (applied or rejected), read
   `state = socket_request(sock, "state", {}, 10.0)` once, then resolve the effort id from
   `parse_config_id_candidates(manifest["acp_effort_config_id"])`. The `effort` record gains
   `"candidates": [...]` and `"advertised": true|false`; `config_id` is the id actually sent. Fast and mode are
   untouched (their ids are single and stable).
3. `effective_selection(manifest, state)` (`:2091`): resolve `effort` through the same helper and add
   `"effort_config_id"` to the returned dict; `explicit_selection_problem` (`:2110`) unchanged.
   `zcode_host_config_state` (`:2068`) unchanged (ZCode Host only).
4. `EXPLICIT_SELECTION_VERIFIED` stays `{"opencode"}` — no new refusal for Cursor; a rejected effort remains a
   limitation receipt (`applied:false` + `error`), as today.
5. Holder (`scripts/kaola-acp-holder.py`): **no change required.** `op_set_config_option` (`:3661`) already mirrors
   the `configOptions` returned by the model set into `session_meta` (`:3677`), which is what the post-apply `state`
   read sees; its reply already carries `option_name`/`value_name`. `initial_config_options` remains the
   `session/new` payload (pre-apply, persisted schema) — a fact for the record, not a selector.
6. Model policy (`scripts/kaola-model-policy.py`): **no change.** `resolve` returns effort by tier/explicit value only;
   `real_surface_evidence` TUI regexes are PTY-only (retired #130) and are not on the ACP start path; the
   `cursor-main-tui` regex already accepts "Grok 4.7 256K Extra High".

## 6. Selection paths after the change (traced against the measured schema)

| start | model sent | effort candidates → resolved | expected receipt |
|---|---|---|---|
| default tier | `grok-4.7` (mapped from `grok-4.7-xhigh`) | advertised `reasoning_effort` → `reasoning_effort=xhigh` | effort applied true, `value_name "Extra High"`, `effective_effort xhigh`, fast `false` applied, effective off |
| `--tier upgrade` | `claude-fable-5-1` (mapped) | `reasoning_effort` not advertised, `effort` advertised → `effort=high` | effort applied true, `value_name "High"`, `effective_effort high` |
| `--model grok-4.7-xhigh-fast` | `grok-4.7`, suffix effort xhigh | `reasoning_effort=xhigh` | fast `true` applied, effective on |
| `--model grok-4.7-xhigh --effort medium` | `grok-4.7` | `reasoning_effort=medium` | explicit effort wins (existing semantics) |
| `--model grok-4.6-xhigh` (unmapped, sent literally) | rejected by the picker (base ids only) | not advertised → literal `reasoning_effort` → rejected | both limitations reported; session usable — unchanged class of outcome |
| `--model gpt-5.6-sol` | applied | neither candidate advertised (`reasoning`) → literal first → -32602 | effort limitation receipt, honest; extending the list to `reasoning` is out of scope (value vocabulary unmeasured) |
| `--resume/--continue` without tier/model/effort | preserved | no effort sent | unchanged |
| PTY | refused `transport-pty-retired` | — | unchanged |

## 7. Templates and docs (generated output only through `./scripts/render-skills.py --write` then `--check`)

- `templates/references/acp.md.tmpl:25`: after "using `{{ACP_MODEL_CONFIG_ID}}`/`{{ACP_EFFORT_CONFIG_ID}}`/`{{ACP_FAST_CONFIG_ID}}`
  when non-empty" add: "an effort id may list `;`-separated candidates in order; the first one the agent advertises
  after the model apply is used (`config_application.effort.candidates`/`advertised`), otherwise the first
  literally". Budget: `references/acp.md` is 5517/8192 B — ample.
- `templates/SKILL.md.tmpl`: no wording change (tier presets unchanged). `skills/cursor-cli-kaola-project-runner/SKILL.md`
  is 11502/12288 B; the quirk text lives in `references/acp.md`, not SKILL.md.
- `docs/api.md:36-40`: describe `acp_effort_config_id` as "an ordered `;` candidate list resolved against the
  advertised options after the model apply" and correct "separate `model`/`effort`/`fast` options" to note the
  per-model option set.
- `CHANGELOG.md`: new `## 0.5.8 — Unreleased` entry (user-visible): "cursor-cli default tier now lands Grok 4.7
  Extra High on Cursor CLI ≥ 2026.09.18: the effort option id follows the selected model
  (`reasoning_effort` for Grok 4.7, `effort` for Claude Fable 5.1); receipts add `config_application.effort.candidates`/`advertised`
  and `effective_selection.effort_config_id`. Fixes #135."
- `templates/grok-golden/` untouched; `skills/` and `hosts/` never hand-edited.

## 8. Tests and validation

`tests/contract/mock-acp-agent.py` (`:397-432`): make the Cursor picker surface per-model, mirroring probe-9 —
`CURSOR_MODEL_OPTIONS = {"grok-4.7": [context, reasoning_effort, fast], "claude-fable-5-1": [thinking, context, effort],
"grok-4.6": [effort, fast]}`; `config_options()` returns mode + model + the set for the currently configured model
(default `grok-4.7`, i.e. the persisted-schema case); `on_set_config` with `strict-config` therefore rejects `effort`
on grok-4.7 with the live text `"Unknown model config option: effort"` and returns the new option set for a model
switch (as the CLI does).

`tests/contract/test-acp-contract.py`:
- `test_cursor_default_exact_order_and_semantics` (`:1681`): events become `[("model","grok-4.7"),("reasoning_effort","xhigh"),("fast","false")]`;
  assert `effort.config_id == "reasoning_effort"`, `effort.advertised is True`, `effective_selection.effective_effort == "xhigh"`.
- `test_cursor_upgrade_tier_maps_fable_base_id` (`:1712`): events stay `("effort","high")`; assert `advertised True`
  and `effective_effort == "high"` — this is the regression guard against a naive flip.
- `test_cursor_explicit_fast_variant_id_decomposes` (`:1728`): `("reasoning_effort","xhigh")`.
- New `test_cursor_effort_candidates_fall_back_literally`: a mock model that advertises neither candidate → literal first
  id sent, `advertised False`, `applied False` with the -32602 error, receipt has no `error`, `send` still works.
- New `test_cursor_manifest_declares_effort_candidates`: manifest value is exactly `reasoning_effort;effort` and
  `acp_verified_versions` carries `cli=2026.09.18-9a7762b` (pattern of `test-issue-88` `:297`).
- `test_cursor_preflight_reports_parameterized_options` (`:1672`): expected ids become `{"model","reasoning_effort","fast"}`.
- Non-Cursor platforms: a single-id manifest must produce byte-identical `config_application` (no `candidates` key
  when the list has one element is acceptable, or always present — pick one and pin it; recommendation: always
  present, cheaper to reason about).

`tests/contract/test-generated-skills.py` (`:243-250`): no change expected; run to confirm the new quirk text leaks no
adapter vocabulary. `tests/contract/test-issue-50-runner-integration.py:184` still parses `acp_verified_versions`.

Gates: `./scripts/render-skills.py --check`, `./scripts/validate.sh` (lanes already include `test-acp-contract.py`,
`test-generated-skills.py`, model-policy lane C), run in the foreground; compare `git diff --check` against base.

## 9. Acceptance smoke (exact)

```bash
SKILL_DIR=<installed cursor-cli Skill of the candidate build>
REPO=/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner
env -u KAOLA_ACP_HEARTBEAT_HOST -u KAOLA_ACP_HEARTBEAT_HOST_SOCKET \
  "$SKILL_DIR/scripts/runtime-tmux.sh" start --repo "$REPO" --session cursor-cli-kaola-i135-smoke | tee smoke-default.json
"$SKILL_DIR/scripts/runtime-tmux.sh" stop --repo "$REPO" --session cursor-cli-kaola-i135-smoke
env -u KAOLA_ACP_HEARTBEAT_HOST -u KAOLA_ACP_HEARTBEAT_HOST_SOCKET \
  "$SKILL_DIR/scripts/runtime-tmux.sh" start --repo "$REPO" --session cursor-cli-kaola-i135-smoke-up --tier upgrade | tee smoke-upgrade.json
"$SKILL_DIR/scripts/runtime-tmux.sh" stop --repo "$REPO" --session cursor-cli-kaola-i135-smoke-up
```

PASS iff `smoke-default.json` has `transport.cli_version` naming 2026.09.18-9a7762b (or newer),
`config_application.model == {applied:true, value:"grok-4.7", requested_id:"grok-4.7-xhigh", mapped:true}`,
`config_application.effort == {applied:true, config_id:"reasoning_effort", value:"xhigh", advertised:true, candidates:[...]}`,
a `configured_options` entry `{config_id:"reasoning_effort", value_name:"Extra High"}`,
`config_application.fast == {applied:true, value:"false"}`, `fast.effective == "off"`,
`effective_selection == {effective_model:"grok-4.7", effective_effort:"xhigh", effort_config_id:"reasoning_effort"}`;
and `smoke-upgrade.json` has `effort.config_id == "effort"`, `value "high"`, `value_name "High"`,
`effective_effort "high"`. Both stops report `stopped:true`; `pgrep -f i135-smoke` is empty.
Never use `/model` as a probe; the receipt is the proof.

## 10. Constraints honored / non-goals / notes

- Prompts over ACP only; no launch-arg, gate, classifier, retry, or waiting layer; the session stays usable on any
  rejection; receipts keep `applied`/`effective` honest.
- Delivery as a PR from `workflow/issue-135`; no sink-merge.
- Not in scope: the stale install roots (`~/.claude/skills`, `~/.cursor/skills` still carry the Sep-21 pre-marker
  Grok 4.6 copy; 17 files differ from the build) — pending-owner deploy item per the issue; gpt `reasoning` id; the
  Host env leak of `KAOLA_ACP_HEARTBEAT_HOST` into workers (pre-existing, tracked separately).
- Side effect to know: every Runner model/effort apply is re-persisted by the CLI into `~/.cursor/cli-config.json`
  (Cursor-native behavior; the probes left it at grok-4.7 / reasoning_effort xhigh / fast false, the ordered default).

HUMAN_DECISION_REQUIRED: none. All choices above are checkable engineering calls inside the authorized scope.

## 11. Implementation checklist (for the impl session)

1. `platforms/cursor-cli.yaml`: three fields per §4.
2. `scripts/kaola-acp.py`: helpers + apply-loop resolution + `effective_selection` per §5.
3. `tests/contract/mock-acp-agent.py` per-model Cursor option sets; tests per §8.
4. `templates/references/acp.md.tmpl`, `docs/api.md`, `CHANGELOG.md` per §7; `./scripts/render-skills.py --write` then `--check`.
5. `./scripts/validate.sh` foreground; `git diff --check` vs base.
6. Install the candidate build into one precedent root, run §9, attach both receipts to the PR.
