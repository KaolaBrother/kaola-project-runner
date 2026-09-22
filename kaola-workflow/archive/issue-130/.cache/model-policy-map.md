# Issue #130 — test-model-policy.sh (Issue #8) guarantees mapped to ACP coverage

Investigated 2026-09-22 in worktree `.kw/worktrees/issue-130` (HEAD 16b42b2 plus uncommitted
parallel #130 edits; the model code in `scripts/kaola-acp.py` / `scripts/kaola-model-policy.py`
is unchanged by those edits: `git diff scripts/kaola-acp.py` only drops the transport
alternatives, the tmux `transport-mismatch` check and `--transport-reason`).

Paths below are relative to that worktree. `T` = `tests/contract/test-model-policy.sh`,
`A` = `tests/contract/test-acp-contract.py`.

## 0. How ACP produces model evidence (read + measured)

- `scripts/kaola-acp.py:1220 resolve_selection()` runs `kaola-model-policy.py resolve`
  (argv list, no shell). Precedence: `--model` → source `user` (candidate = literal, effort only
  if `--effort`); `--resume/--continue` without model/effort/tier → `resume-preserved`;
  otherwise the tier preset `runner-<tier>`.
- `scripts/kaola-model-policy.py:160 resolve()` always returns
  `actual_runtime_model_id: None`, `actual_parameters: None`, `model_verified: "unknown"`,
  `model_mismatch_reason: "actual-model-evidence-not-yet-read"` (L305-308). **Nothing on the ACP
  path ever calls `verify`** (the only `verify` caller was the PTY branch of `kaola-tmux.sh`,
  HEAD L458, now gone). So on ACP these four fields are constants.
- `merge_policy_evidence()` (`kaola-acp.py:1300`) copies to the start/preflight receipt, top level:
  `requested_model_source, requested_model_name, requested_tier, requested_fast,
  resolved_runtime_model_id, resolved_runtime_model_display, resolved_parameters, resolved_fast,
  actual_runtime_model_id, actual_parameters, model_verified, model_mismatch_reason,
  model_evidence_provenance` + `model_selection {source, tier, requested_name, resolved_model,
  resolved_effort, preserved}`.
- The real ACP "actual" evidence is different keys:
  - `config_application.{model,effort,fast,mode}` = `{applied, config_id, value, error?,
    requested_id?, mapped?, declared?}` (`kaola-acp.py:2340-2375`)
  - `effective_selection = {effective_model, effective_effort}` = the agent's advertised
    `configOptions[].currentValue` after config (`kaola-acp.py:1805`, set at L2498-2499,
    start only).
  - `fast = {requested, support, effective, applied, applied_via, detail?, conflict?}`
    (`fast_report`, L1405).
- A mismatch between `effective_selection` and the resolved model is a **gate only** for
  `opencode` with explicit `--model/--effort` (`EXPLICIT_SELECTION_VERIFIED`, L1802,
  refusal `explicit-selection-unverified`) and for a ZCode Host session (`host-model-mismatch`
  before spawn, `host-model-unverified` after). For every other case it is reported and nothing
  else happens; `model_verified` stays `"unknown"`.
- `status`/`observe` (`kaola-acp.py:2766`) = holder `op_state` + `record`. It carries
  `session_meta.configOptions` (with `currentValue`) and `initial_config_options`, and **none**
  of the model-policy keys above.

Measured with a scratch driver (`/tmp/kpr130-mp/run.py`, codex platform, mock agent,
isolated `KAOLA_ACP_RECORD_ROOT`, `CODEX_BIN` = a fake that exits 1, all inherited
`KAOLA_*`/`KPR_*` removed):

| case | requested_model_name / resolved_runtime_model_id | config_application.model | effective_selection | model_verified / reason | error |
|---|---|---|---|---|---|
| default | `GPT-5.6 Sol High` / `gpt-5.6-sol` | applied, `gpt-5.6-sol` | null/null | unknown / not-yet-read | none |
| `--model gpt-6-astra --effort low` | verbatim / verbatim, source user | applied | null/null | unknown / not-yet-read | none |
| hostile literal `model with spaces (x) [y]; $(touch …/pwn); \`touch …/pwn.bt\`` | verbatim both | applied, verbatim value | null/null | unknown | none; marker files **not** created |
| `--model unavailable/codex` (permissive mock) | verbatim | applied True | null/null | unknown | none |
| same, `--caps strict-config` | verbatim | applied False, `error.code=config-option-failed`, detail -32602 | null/null | unknown | none |
| default + `MOCK_ACP_CONFIG` currentValue `saved-picker/other` | `gpt-5.6-sol` | applied True | `saved-picker/other` / `high` | unknown / not-yet-read | none (not refused) |
| `status` after `user` / `mismatch` | — | — | — | no model key present anywhere in status or `status.record` | — |

The status of the mismatch session reported `session_meta.configOptions` model
`currentValue: saved-picker/other`. The hostile literal also went through the shared entrypoint
(`bash scripts/kaola-tmux.sh codex start … --model "$M"` with `KAOLA_ACP_COMMAND`=mock): it
came back verbatim in `requested_model_name` and `config_application.model.value`, and no
marker file was created. No holder or mock processes were left running afterwards
(`ps | grep mock-acp-agent|kaola-acp-holder` was empty).

## 1. Guarantees asserted by test-model-policy.sh

The PTY suite loops over 8 platforms (grok claude-code opencode kimi-cli cursor-cli devin codex
droid; T:450). `assert_model_evidence` (T:62-137) checks, on every receipt:
source, requested name, resolved id, actual id (or unreadable), `model_verified`,
`resolved_parameters.effort`, `fast is False` for `grok-4.7-xhigh`, `actual_parameters` dict/None,
`model_mismatch_reason` empty iff verified, `model_evidence_provenance` present with
catalog/resolution/requested **and** actual/runtime/tui/session when verified ∈ {true,false}.

| # | class | guarantee (PTY test name) | T lines |
|---|---|---|---|
| G1 | extra: contract shape | preflight carries all 8 model keys (`json_has_model_contract`) | 27-60, 510-522 |
| G2 | extra: tiers | preflight default/upgrade: source `runner-default`/`runner-upgrade`, preset name/id/effort, actual unreadable, verified `unknown` | 523-537 |
| G3 | extra: tiers | start default overrides a saved picker: resolved id launched, actual == resolved, verified true; saved picker never launched | 539-563 |
| G4 | (e) | `status` repeats the same model evidence + provenance as start | 547-549, 557-559 |
| G5 | extra: tiers | start `--tier upgrade` launches the upgrade id, verified true | 568-586 |
| G6 | (c) | `--model X --effort E` → source `user`, name/resolved/actual = X, verified true, effort E | 588-611 |
| G7 | extra: effort | `--model X` without `--effort` → no preset effort attached | 613-624 |
| G8 | (b) | `--model unavailable/<p>` is not a gate: launched literally, reported verbatim | 626-640 |
| G9 | (d) | actual ≠ resolved → verified `false`, non-empty reason, start not blocked | 642-658 |
| G10 | (f) | actual unreadable → actual null/unknown, verified `unknown`, reason non-empty, not blocked | 660-676 |
| G11 | extra: resume | `--continue` → source `resume-preserved`, name `native saved session selection`, no model/effort flags, verified unknown | 678-695 |
| G12 | extra: resume | `--resume ID` → same as G11 | 697-706 |
| G13 | extra: resume | `--resume ID --tier upgrade` → tier overrides preservation | 708-722 |
| G14 | (c)+(d) | `--resume ID --model X` where the resumed session keeps the saved model → reports source user, resolved X, actual saved, verified false (does not claim the override took) | 724-741 |
| G15 | (a) | hostile model string reported verbatim (requested/resolved/actual), start not refused | 743-754 |
| G16 | (a) | hostile model string never executed as shell | 745-746, 755-756 |
| G17 | extra: fast | codex `service_tier=default` off / `fast` on; cursor `--fast on` → catalog `-fast` variant, upgrade+fast → `resolved_fast=unsupported`; devin preset fast → `unsupported`; claude `--settings fastMode` false/true, explicit model + fast passed verbatim; other platforms `resolved_fast=unsupported` | 762-882 |
| G18 | extra: no injection | the Runner never writes `workflow-next` into the session on any start | 187-192, every case |
| G19 | extra: opencode | preset keeps the CLI's own opening model (no `--model/--variant`); user model rides `OPENCODE_CONFIG_CONTENT` not argv | 523-553, 600-608 |
| G20 | (f) verify unit | launch preamble / pane `exec … --model X` line is not actual evidence (opencode, kimi, codex) | 886-926 |
| G21 | verify unit | last confirmed model survives a scrolled frame (grok) | 928-949 |
| G22 | verify unit | Cursor 2026.09.15 `Grok 4.7 256K Extra High Fast` footer parses to `grok-4.7-xhigh-fast` | 951-969 |

## 2. Mapping to ACP coverage

| # | class | ACP coverage (file:line — what it asserts) | verdict |
|---|---|---|---|
| G1 | shape | A:1200 `test_preflight_reports_advertised_config_ids_and_selection` — advertised ids/options, `model_selection.resolved_model == gpt-5.6-sol`, `config_application.applied False`. Does not assert the top-level policy keys. | PARTIAL |
| G2/G3/G5 | tiers | A:1107 `test_codex_default_applies_model_effort_fast_mode_in_order` (exact set order model→effort→fast→mode, applied, `model_selection.source runner-default`, tier, resolved_model); A:1132 upgrade → `gpt-6-astra`, `runner-upgrade`; A:1276/1307 cursor default/upgrade mapping; `test-droid-acp-contract.py:134,256,272` default/core/upgrade; `test-issue-111-model-tiers.py:279-305` undeclared tier refused, `:325,336` tier→manifest mapping; `test-issue-119-host-entry.py:469` Host resolves exactly the worker default. "verified true" cannot exist on ACP (loss, §4). | COVERED (selection); verification = loss |
| G4 | (e) status provenance | none. Measured: status has no `requested_model_source`/`model_selection`/`resolved_*`/`effective_selection`; only `session_meta.configOptions[].currentValue`. | MISSING (and a behavior loss) |
| G6 | (c) user override | A:1142 `test_codex_bare_explicit_model_gets_no_invented_effort` (`("model","gpt-6-astra")` sent, `model_selection.source == "user"`); A:1152 explicit effort sent; `test-droid-acp-contract.py:204,212,223`; `test-issue-119-host-entry.py:510-514` opencode honored explicit → `effective_selection` equals request. No assertion of `requested_model_name`/`resolved_runtime_model_id` values. | COVERED (fresh start) |
| G7 | effort | A:1142 (`effort.reason == "no-resolved-value"`, no `reasoning_effort` set); droid :204 | COVERED |
| G8 | (b) unavailable | A:1172 `test_codex_rejected_model_is_limitation_not_failure` — `--model unavailable/model` with `strict-config`: start has no error, `config_application.model.applied False` + error, effort/fast still applied, a later send completes. Does not assert the literal is reported verbatim (`requested_model_name`, `resolved_runtime_model_id`, `config_application.model.value`) or source `user`; the accepted (non-strict) path is untested. | PARTIAL |
| G9 | (d) mismatch | Gated cases only: `test-issue-119-host-entry.py:515-530` (opencode explicit model ignored → **refused** `explicit-selection-unverified`, holder stopped); `test-zcode-heartbeat-contract.py:1927` (`host-model-mismatch`), `:2047` (`host-model-unverified`). For an ordinary worker, nothing tests that `effective_selection` ≠ resolved is reported and the start is **not** blocked. ACP never sets `model_verified false`. | MISSING (non-gated platforms); gated divergences are owner-ruled (#108, #119 H2) |
| G10 | (f) unreadable | Holds by construction (verified is the constant `unknown`; `effective_selection` nulls when no `currentValue` — the default mock advertises none). No test asserts it. The reason string differs: `actual-model-evidence-not-yet-read`, not `actual-model-evidence-unreadable`. | MISSING (test); semantics PARTIAL |
| G11/G12 | resume | A:1187 `test_codex_resume_preserves_saved_selection` (no model/effort set, `model_selection.preserved True`, `resolved_model None`); `test-issue-50-runner-integration.py:507` claude `--continue` → `resume-preserved` | COVERED |
| G13 | resume+tier | none | MISSING |
| G14 | resume+model override not claimed | none (no ACP test combines `--resume` with `--model`) | MISSING |
| G15 | (a) hostile reported verbatim | none. Measured: reported and applied verbatim, not refused. | MISSING (behavior holds) |
| G16 | (a) not executed | none on ACP. Measured: not executed (argv lists end to end; kaola-tmux.sh forwards `--model "$model"` quoted, `scripts/kaola-tmux.sh:185`). | MISSING (behavior holds) |
| G17 | fast | A:1107 codex off, A:1156 codex on, A:1212 codex rejected → `unknown`, A:1162 grok on → `unsupported`, A:1230 devin fast-variant rejected → `unknown`/`model-id`, A:1323/1336 cursor fast. PTY-only mechanisms (codex `-c service_tier`, cursor catalog `-fast` variant resolution, claude `--settings fastMode`) have no ACP counterpart; claude ACP fast goes through the `fast` config option, which no ACP test exercises. | COVERED for ACP mechanisms; PTY mechanisms = loss |
| G18 | no workflow injection | none; holds by construction (ACP start sends no `session/prompt`) | MISSING (cheap) |
| G19 | opencode | `test-issue-119-host-entry.py:501-507` plain start reports the agent's own opening selection (`native/opening`); :510-514 explicit honored. The `OPENCODE_CONFIG_CONTENT` argv route is PTY-only. | COVERED (ACP semantics) |
| G20-G22 | verify() parsing | PTY frame parsing only; `verify` has no ACP caller | N/A — delete with `verify()` / record as loss |

## 3. Test sketches for the PARTIAL/MISSING classes

Put these in `tests/contract/test-acp-contract.py` class `Issue34ModelSelectionAcpTests`
(A:1041). It already provides `cli()` (per-platform, `extra_env`, `caps`), `start()` (sets
`_started`/`_started_platform`, so `AcpSessionFixture.tearDown` runs `stop --force` on the
right platform, A:193-198), `config_events()` (reads `set_config_option` from `MOCK_ACP_LOG`),
and `setUp` truncates the mock log. `tearDownClass` fails on any leaked process under the fixture
root (A:181-188). Do not subclass it: that re-runs every parent test.

Mock facts (`tests/contract/mock-acp-agent.py`):
- `--caps strict-config` rejects any value not in the advertised options with -32602 (L457-471).
- Default `CONFIG_OPTIONS` (L365) have **no `currentValue`** → `effective_selection` is
  `{None, None}`: this is the unreadable baseline.
- `MOCK_ACP_CONFIG` JSON (L128-146): `new` (configOptions in session/new; `null` omits them),
  `resume`, `set_result` (returned for **every** set_config_option call), `set_error`,
  `set_drop`, `set_notify`. The holder mirrors returned `configOptions` into
  `session_meta` (holder L1466, L3649), which is what `effective_selection` and `status` read.
- Every inbound prompt logs `{"event": "prompt", ...}` (L706).

Hermeticity: the fixture does not override `CODEX_BIN`, so `resolve()` runs the real
`codex debug models` / `--help` on a machine that has codex (5 s timeout each,
`KAOLA_MODEL_PROBE_TIMEOUT`). None of the assertions below depend on the catalog. To make the
probes deterministic, pass `extra_env={"CODEX_BIN": "/nonexistent"}`: the probe then fails with
OSError, and `resolution.state` becomes `catalog-unknown-declared-candidate`.

Leak safety (#77): `start()` sets `_started` only after the CLI returns. If `cli()` raises
(timeout or bad JSON) after the holder has spawned, tearDown will not stop it. For new tests,
prefer `self.addCleanup(self.cli, "stop", "--force", platform="codex", check=False, timeout=15)`
**before** calling start.

```python
MISMATCH_CONFIG = {"set_result": {"configOptions": [
    {"id": "model", "type": "select", "currentValue": "saved-picker/other",
     "options": [{"value": "gpt-5.6-sol"}, {"value": "gpt-6-astra"}]},
    {"id": "reasoning_effort", "type": "select", "currentValue": "high", "options": []},
]}}

def _guarded_start(self, *args, **kwargs):
    self.addCleanup(self.cli, "stop", "--force", platform="codex", check=False, timeout=15)
    return self.start("codex", *args, **kwargs)

# (a) G15+G16 — hostile id is data, reported and applied verbatim, never executed
def test_hostile_model_id_is_reported_and_applied_verbatim(self) -> None:
    marker = self.root / "model-input-executed"
    hostile = f"model with spaces (x) [y]; $(touch {marker}); `touch {marker}.bt`"
    receipt = self._guarded_start("--model", hostile)
    self.assertIsNone(receipt.get("error"), receipt)
    self.assertNotEqual(receipt.get("result"), "refused")
    self.assertEqual(receipt["requested_model_source"], "user")
    self.assertEqual(receipt["requested_model_name"], hostile)
    self.assertEqual(receipt["resolved_runtime_model_id"], hostile)
    self.assertEqual(receipt["model_selection"]["resolved_model"], hostile)
    self.assertEqual(receipt["config_application"]["model"]["value"], hostile)
    self.assertIn(("model", hostile), self.config_events())
    self.assertFalse(marker.exists())
    self.assertFalse(Path(f"{marker}.bt").exists())

# (a) optional: the same through the shared bash entrypoint (the quoting layer T exercised)
def test_hostile_model_id_survives_the_shared_entrypoint(self) -> None:
    marker = self.root / "entrypoint-executed"
    hostile = f"m (x); $(touch {marker}); `touch {marker}.bt`"
    env = self.env() | {"KAOLA_ACP_COMMAND": self.mock_command()}
    tmux = PROJECT / "scripts" / "kaola-tmux.sh"
    self.addCleanup(subprocess.run, ["bash", str(tmux), "codex", "stop", "--repo", str(self.repo),
                    "--session", self.session, "--force"], env=env, capture_output=True, timeout=30)
    out = subprocess.run(["bash", str(tmux), "codex", "start", "--repo", str(self.repo),
                          "--session", self.session, "--model", hostile],
                         env=env, capture_output=True, text=True, timeout=60)
    receipt = json.loads(out.stdout)
    self.assertEqual(receipt["requested_model_name"], hostile)
    self.assertEqual(receipt["config_application"]["model"]["value"], hostile)
    self.assertFalse(marker.exists()); self.assertFalse(Path(f"{marker}.bt").exists())

# (b) G8 — unavailable literal: sent verbatim, reported, never a start gate (both agent answers)
def test_unavailable_model_accepted_by_agent_is_reported_verbatim(self) -> None:
    receipt = self._guarded_start("--model", "unavailable/codex")
    self.assertIsNone(receipt.get("error"), receipt)
    self.assertEqual(receipt["requested_model_source"], "user")
    self.assertEqual(receipt["requested_model_name"], "unavailable/codex")
    self.assertEqual(receipt["resolved_runtime_model_id"], "unavailable/codex")
    self.assertEqual(receipt["config_application"]["model"],
                     {"applied": True, "config_id": "model", "value": "unavailable/codex"})

def test_unavailable_model_rejected_by_agent_is_reported_verbatim(self) -> None:
    # extends A:1172 with the verbatim-report assertions it lacks
    receipt = self._guarded_start("--model", "unavailable/codex", caps="strict-config")
    self.assertIsNone(receipt.get("error"), receipt)
    self.assertEqual(receipt["requested_model_name"], "unavailable/codex")
    self.assertEqual(receipt["resolved_runtime_model_id"], "unavailable/codex")
    model = receipt["config_application"]["model"]
    self.assertFalse(model["applied"])
    self.assertEqual(model["value"], "unavailable/codex")
    self.assertEqual(model["error"]["code"], "config-option-failed")
    self.assertEqual(self.cli("send", "--text", "usable", platform="codex")["outcome"], "turn_completed")

# (d) G9 — agent reports another model: evidence, not a gate (non-gated platform)
def test_effective_model_mismatch_is_reported_not_a_gate(self) -> None:
    receipt = self._guarded_start(extra_env={"MOCK_ACP_CONFIG": json.dumps(MISMATCH_CONFIG)})
    self.assertIsNone(receipt.get("error"), receipt)
    self.assertNotEqual(receipt.get("result"), "refused")
    self.assertEqual(receipt["state"], "ready")
    self.assertEqual(receipt["resolved_runtime_model_id"], "gpt-5.6-sol")
    self.assertTrue(receipt["config_application"]["model"]["applied"])
    self.assertEqual(receipt["effective_selection"],
                     {"effective_model": "saved-picker/other", "effective_effort": "high"})
    # Pins today's ACP semantics; not the PTY "false" (see loss L3):
    self.assertEqual(receipt["model_verified"], "unknown")
    self.assertEqual(self.cli("send", "--text", "still usable", platform="codex")["outcome"],
                     "turn_completed")

# (c)+(d) G14 — resume + explicit model: the request is reported, the agent's answer is separate
def test_resume_with_explicit_model_reports_request_and_agent_answer(self) -> None:
    pages = [{"sessions": [{"sessionId": "saved-codex-1", "cwd": str(self.repo)}]}]
    receipt = self._guarded_start("--resume", "saved-codex-1", "--model", "gpt-6-astra",
        caps="resume", extra_env={"MOCK_ACP_LIST_PAGES": json.dumps(pages),
                                  "MOCK_ACP_CONFIG": json.dumps(MISMATCH_CONFIG)})
    self.assertIsNone(receipt.get("error"), receipt)
    self.assertEqual(receipt["model_selection"]["source"], "user")
    self.assertFalse(receipt["model_selection"]["preserved"])
    self.assertIn(("model", "gpt-6-astra"), self.config_events())
    self.assertEqual(receipt["effective_selection"]["effective_model"], "saved-picker/other")

# G13 — resume + tier overrides preservation
def test_resume_with_tier_applies_the_tier(self) -> None:
    pages = [{"sessions": [{"sessionId": "saved-codex-1", "cwd": str(self.repo)}]}]
    receipt = self._guarded_start("--resume", "saved-codex-1", "--tier", "upgrade", caps="resume",
                                  extra_env={"MOCK_ACP_LIST_PAGES": json.dumps(pages)})
    self.assertEqual(receipt["model_selection"]["source"], "runner-upgrade")
    self.assertFalse(receipt["model_selection"]["preserved"])
    self.assertIn(("model", "gpt-6-astra"), self.config_events())

# (e) G4 — status carries the agent's native selection (the only model fact ACP status has)
def test_status_reports_the_native_selection_after_start(self) -> None:
    self._guarded_start("--model", "gpt-6-astra",
        extra_env={"MOCK_ACP_CONFIG": json.dumps({"set_result": {"configOptions": [
            {"id": "model", "type": "select", "currentValue": "gpt-6-astra", "options": []}]}})})
    status = self.cli("status", platform="codex")
    options = {o["id"]: o for o in (status.get("session_meta") or {}).get("configOptions") or []}
    self.assertEqual(options["model"]["currentValue"], "gpt-6-astra")
    # Loss L1 pinned so re-adding provenance is a deliberate change:
    self.assertNotIn("requested_model_source", status)
    self.assertNotIn("model_selection", status)

# (f) G10 — no readable currentValue → unknown, never a guess, never a gate
def test_unreadable_effective_model_is_unknown(self) -> None:
    receipt = self._guarded_start()   # default mock options carry no currentValue
    self.assertIsNone(receipt.get("error"), receipt)
    self.assertEqual(receipt["effective_selection"],
                     {"effective_model": None, "effective_effort": None})
    self.assertIsNone(receipt["actual_runtime_model_id"])
    self.assertIsNone(receipt["actual_parameters"])
    self.assertEqual(receipt["model_verified"], "unknown")
    self.assertTrue(receipt["model_mismatch_reason"])  # "actual-model-evidence-not-yet-read"

# variant: agent advertises no configOptions at all (MOCK_ACP_CONFIG {"new": null, "set_result": {}})
#   → same effective_selection nulls, start still ready.

# G18 — start never writes a prompt (so never workflow-next)
def test_start_writes_no_prompt(self) -> None:
    self._guarded_start()
    self.assertEqual([e for e in self.read_mock_log() if e.get("event") == "prompt"], [])
```

G1 (shape): add to A:1200 a loop asserting that each of the 13 `merge_policy_evidence` keys is
present in the preflight receipt.

## 4. Loss statements (PTY exposed; ACP does not). These are not tests.

- L1 `status` model provenance (G4). PTY `status` returned the full model evidence. ACP
  `status`/`observe` returns none of `requested_model_source`, `requested_model_name`,
  `requested_tier`, `resolved_*`, `model_selection`, `model_evidence_provenance`,
  `effective_selection`. These exist only in the one-shot start receipt, and the holder
  `record.json` does not persist them. What remains is `session_meta.configOptions[].currentValue`
  and `initial_config_options`. If the guarantee is required, it needs an implementation change
  (for example, persisting `model_selection` in the record). That is the caller's call.
- L2 `actual_runtime_model_id`, `actual_parameters`: always `null` on ACP. The nearest
  substitute is `effective_selection.{effective_model,effective_effort}` (start only).
- L3 `model_verified` true/false and `model_mismatch_reason` values
  `actual-model-mismatch:<id>`, `actual-<key>-mismatch:<v>`, `actual-model-evidence-unreadable`:
  ACP always reports `"unknown"` / `"actual-model-evidence-not-yet-read"`. No field computes a
  match or mismatch outside the opencode and ZCode-Host gates.
- L4 `model_evidence_provenance.actual` / `.latest_observation` (TUI source, e.g.
  `grok-main-tui`, `cursor-main-tui`) and "last confirmed survives a scrolled frame" (G21): no ACP
  equivalent. `verify()` in `scripts/kaola-model-policy.py:450` becomes dead code.
- L5 PTY `model` sub-object (`d["model"]["resolved_fast"]`, T:803; the key set in
  `tests/contract/test-guarded-actions.sh:102` includes `model`). ACP puts these at top level
  (`resolved_fast`) plus `fast`.
- L6 PTY-only launch mechanisms: codex `-c service_tier`, cursor catalog `-fast` variant chosen
  from the CLI catalog, claude `--settings {"fastMode": …}`, opencode `OPENCODE_CONFIG_CONTENT`
  model carriage, kimi `KIMI_MODEL_THINKING_EFFORT`. ACP carries them as config options, or not
  at all.
- L7 Divergence, not loss: on ACP a mismatch **is** a gate for opencode explicit selections
  (#119 H2) and for ZCode Host sessions (#108), where PTY's rule was "mismatch is evidence, never
  a gate". Both are owner-ruled.
