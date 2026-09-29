# Issue #227 — DSH latest native ACP compatibility evidence (2026-09-29)

## Registry (reconfirmed at start)

`npm view @deepseek-ai/dsh dist-tags`: latest `0.1.7-rc.2`, next `0.2.0-rc.1`, alpha `0.1.7-alpha.2`.
Target: latest `0.1.7-rc.2`.

## Isolation

- Install: `npm install --prefix /tmp/kpr-227/npm @deepseek-ai/dsh@0.1.7-rc.2` (task-owned cache).
- Home: `DSH_HOME=/tmp/kpr-227/home`; test repo `/tmp/kpr-227/repo`.
- Credential: the acp profile patch points `credentials` at the existing
  `~/.dsh/.credentials.yaml` with `watch: false` (read in place; never copied, printed, or
  written; mtime unchanged, Sep 23 17:11). No login.
- Shared `~/.local/bin/dsh` (0.1.5-rc.3), real `~/.dsh`, and other live seats were not modified.

## Versions actually loaded

| Fact | Value |
|---|---|
| Launcher | `/tmp/kpr-227/npm/node_modules/.bin/dsh` → `@deepseek-ai/dsh` 0.1.7-rc.2 |
| Agent process argv | `node /tmp/kpr-227/npm/node_modules/.bin/dsh --profile acp` (ps of `agent_pid`) |
| Bundles | `dsh-base`, `dsh-acp-app`, `dsh-acp` all 0.1.7-rc.2, resolved from the launcher install; profile `node_modules` empty |
| `@earendil-works/pi-ai` | 0.85.1 |
| `agentInfo` | `deepseek-harness-acp/0.0.1`; protocolVersion 1; authMethods []; sessionCapabilities {close,list,resume} |

## Runner lifecycle (worktree Skill `skills/dsh-kaola-project-runner/scripts/runtime-tmux.sh`, `--tier default`)

| Check | Result |
|---|---|
| preflight | ready, runtime_version 0.1.7-rc.2 |
| start | ready; mode applied via env `DSH_PERMISSION_MODE=danger-full-access` |
| model wire (stock catalog) | **FAIL** `-32602 unknown model option: ["opencode-go","deepseek-v4.1-flash"]`; effective stays `["deepseek-official","deepseek-v4-flash"]` (reported honestly, start not blocked) |
| model wire (declared route) | applied, `currentValue ["opencode-go","deepseek-v4.1-flash"]` |
| send/capture (declared route, no session header) | **FAIL** `-32603 … 400 MissingSessionID … x-opencode-session` |
| send/capture (declared route + header) | PASS `KPR-227-OK`, end_turn, 3.5 s |
| cancel | PASS `turn_canceled`, stopReason `cancelled` |
| stop → start --resume same id | PASS; same acp_session_id, model preserved (`resume-preserved`), context recalled `KPR-227-OK` |
| default permission tool turn | PASS; shell write in workspace, 0 permission requests |
| exact stop | PASS every seat; residual_pids [] ; agent pids gone |

Requested / resolved / applied / current model: `DeepSeek V4.1 Flash` (runner-default) /
`opencode-go/deepseek-v4.1-flash` / applied only with the declared route / current
`["opencode-go","deepseek-v4.1-flash"]`. `actual_runtime_model_id` stays unknown (no native
readback). Preflight `catalog-missing-declared-candidate` is the pre-existing `--version` probe
fact, not a gate.

## Causes of the two failures (upstream, not KPR adapter)

1. The shared 0.1.5-rc.3 install carries two local hand edits: pi-ai
   `providers/data/opencode-go.json` adds `deepseek-v4.1-flash` (mtime 17:16 vs 17:00 install),
   and `dsh-llm-pi-ai/lib/index.js` sends `x-opencode-session` (17:01). Stock 0.1.7-rc.2 has neither.
2. dsh 0.1.7 removed `$DSH_HOME/settings.yaml`: first boot of any profile renames it to
   `settings.yaml.imported` and imports its sections into *that* profile's `cordis.patch.yml` only.
3. dsh 0.1.7 refuses `--from-default-profile acp` (shipped name) and materializes the shipped acp
   profile on first boot.

Operator route used in the isolated acp profile patch (no secret):

```yaml
- id: llm-pi-ai
  config:
    providers:
      opencode-go:
        apiKeyEnv: OPENCODE_GO_API_KEY
        api: openai-completions
        baseURL: https://opencode.ai/zen/go/v1
        headers: {User-Agent: dsh/0.1.5-rc.3, x-opencode-session: kpr-227-<uuid>}
        models: [{id: deepseek-v4.1-flash, name: DeepSeek V4.1 Flash, contextWindow: 1000000,
                  maxTokens: 384000, input: [text, image], reasoningEfforts: {low: low, high: high, max: max},
                  compat: {supportsStore: false, supportsDeveloperRole: false, maxTokensField: max_tokens,
                           requiresReasoningContentOnAssistantMessages: true, thinkingFormat: deepseek}}]
```

The declared `models` list replaces the route's whole stock catalog, and a static session header
is shared by every session on that route. This is a workaround, not stock behavior.

## Code diff 0.1.5-rc.3 → 0.1.7-rc.2 (ACP-relevant)

- `dsh-acp`: 19 diff lines, tool-result message shape only; method surface, initialize, approval
  (`session/request_permission` under non-danger modes) unchanged.
- `dsh-base`: `DSH_PERMISSION_MODE` sandbox/approval wiring byte-identical.

## next 0.2.0-rc.1 (static inspection only, untested live)

`dsh-acp`, `dsh-acp-app`, `dsh-settings`, `dsh-llm-pi-ai` byte-identical to 0.1.7-rc.2; `dsh-base`
adds an `otel` entry and moves the telemetry URL. No ACP change seen; same catalog/header gap
expected. Not adopted.

## Not tested

workspace-write / read-only `session/request_permission` round trip (code unchanged); steering
`-32601` method re-probe (dsh-acp method table unchanged); 0.2.0-rc.1 live.

## KPR finding outside this issue

`start` launches the manifest `acp_command` word `dsh` from PATH and ignores `DSH_BIN`, while
`preflight` reports the `DSH_BIN` version. The first seat here ran shared 0.1.5-rc.3 while
preflight said 0.1.7-rc.2. Proof above uses PATH-prepended launches with argv checked by pid.

## Validation

`render-skills.py --write`/`--check` PASS; `test-issue-98-dsh-acp.py` 37 OK;
`test-generated-skills.py` PASS; `./scripts/validate.sh` exit 0 (bash 3.2: watchdog SKIP rows).

## Repair round (Delegator scoped review of 4e4c0cd7)

The live lifecycle receipts above are kept as recorded and were not rerun.

1. The verified record is conditional:
   `acp_verified_versions: cli=0.1.7-rc.2;agent=deepseek-harness-acp/0.0.1;protocol=1;condition=operator-declared-opencode-go-route`.
   Stock DSH 0.1.7-rc.2 is not called compatible out of the box.
2. `DSH_BIN` launch defect fixed in `scripts/kaola-acp.py`. The new `manifest_launch_command`
   helper applies only to dsh (`LAUNCH_BINARY_ENV_PLATFORMS`), and only to a manifest or tier
   command whose first word is `binary_name`. Precedence stays `--command` > `KAOLA_ACP_COMMAND`
   > manifest/tier command. An unset `DSH_BIN` keeps the PATH lookup.
   - Regression `tests/contract/test-issue-98-dsh-acp.py::Issue227LaunchUsesDshBin` (4 tests)
     uses fake `dsh` binaries that record their launch argv.
     - Pre-fix code (HEAD `4e4c0cd7` `kaola-acp.py`): `test_dsh_bin_is_the_launched_binary` FAIL
       (`'path …/path/dsh --profile acp' != 'dsh-bin …/pinned/dsh --profile acp'`), and
       `test_other_platforms_keep_their_command` ERROR (the helper did not exist yet).
     - Fixed code: all 4 OK; the whole file runs 41 OK.
   - Live argv proof: PATH `dsh` = `~/.local/bin/dsh` 0.1.5-rc.3, and
     `DSH_BIN=/tmp/kpr-227/npm/node_modules/.bin/dsh` 0.1.7-rc.2. A checkout start (`baseline_exempt`
     true) of session `dsh-kaola-i227-binfix` launched agent argv
     `node /tmp/kpr-227/npm/node_modules/.bin/dsh --profile acp` with agentInfo
     `deepseek-harness-acp/0.0.1`. Exact stop: residual_pids [], exit 0. Before the fix, the same
     setup launched the PATH 0.1.5-rc.3 binary (session `dsh-kaola-i227-smoke` above).
   - A start through an installed-layout Skill copy is refused `worker-skill-build-skew` until the
     Skills are reinstalled. That is expected, and no install was done.
3. The recovery path is in `platform.md` §Launch (rendered from `launch_summary`): the exact
   `llm-pi-ai` patch entry, stated limits (the declared models list replaces the stock catalog, and
   the static header is shared by every session), and a proof step in a throwaway `DSH_HOME`.
   There is no fallback and no migration by the Runner.
4. `acp_quirks` is condensed to one short 0.1.7 fact plus a pointer to `platform.md` Launch.

Validation for this round:
- `render-skills.py --check`: PASS.
- `test-issue-98-dsh-acp.py`: 41 OK.
- `test-generated-skills.py`: PASS, after the exact dsh-route exemptions for
  `x-opencode-session` and `OPENCODE_GO_API_KEY`.
- `./scripts/validate.sh`: run once because the shared `kaola-acp.py` changed. Its only failure
  was that leakage test, since fixed and rerun. Watchdog rows were skipped on bash 3.2.

## Recheck correction (Delegator review of 9203b691)

Doc-only change. The recovery proof step no longer asks preflight to list the model. The preflight
catalog probe runs `--version` only and reports `catalog-missing-declared-candidate`, so it cannot
list the model. The step now reads: `start`, check that `config_application.model` is applied, check
the `observe`/`status` model `currentValue`, then one `send` in the isolated home. The patch nesting
is now written as `config.providers.opencode-go`. Rerun after the change: render `--check` PASS,
`test-generated-skills.py` PASS, `test-issue-98-dsh-acp.py` OK. The earlier code and live checks
still apply, because no code changed.
