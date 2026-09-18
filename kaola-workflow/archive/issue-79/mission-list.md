# Goal: ZCode 3.12+ ACP app-server compatibility in the Runner-owned adapter, proven by a live model turn

Run: issue-79 · Issue: #79 · Branch: `workflow/issue-79`
Worktree: `/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-79`
Scope lock: #79 only. Never edit or revert #69 / #74 / #75 / #78 runs, branches, worktrees, or sessions.
Standing constraints: no credential copy/decrypt/print; secrets in memory only and redacted in every
log, receipt, comment, fixture, and evidence file; no global/user ZCode config mutation; no
auth-provider widening; no upstream byte vendoring; no hand-edit of generated `skills/`; no release
and no global install; do NOT finalize/archive/sink before outer ACCEPT.

## 1. Upstream primary-source facts for ZCode 3.12+
- item: From primary upstream sources only (william0wang/zcode-acp CHANGELOG v0.42.2-v0.42.5, docs/TROUBLESHOOTING.md, docs/PROTOCOL.md), establish exact facts: the bundled provider-config env var name(s) and expected value, the 3.12+ model/provider snapshot request shape that replaces the v0.39.0 `runtimeModel` key on `session/create` and `session/setModel`, and the per-turn `interaction/requestProviderRuntimeHeaders` request/response contract. Record verbatim quotes and source URLs; no conjecture.
- status: done
- dispatched: knowledge-lookup subagent; output lands at `kaola-workflow/issue-79/evidence/01-upstream-facts.md` in the main checkout
- result: `evidence/01-upstream-facts.md` (sources retrieved 2026-09-18). Decisive facts:
  (1) TWO env vars — `ZCODE_BUILTIN_PROVIDER_CONFIG_FILE` resolved from the CLI **entry script** as
  `dirname(entry)/provider/zcode-builtin.json` else `dirname(entry)/../config/provider/zcode-builtin.json`
  (first existing wins), and `ZCODE_PERSONAL_PROVIDER_CONFIG_FILE` = `~/.zcode/v2/provider_config.json`.
  Upstream states both are needed or the CLI re-syncs the table into a version-keyed runtime copy and
  rewires `configRevision` to that copy's path (upstream code nonetheless returns builtin-only when the
  personal file is absent — recorded tension).
  (2) `session/create` carries NO model key (workspace, mode, optional mcpServers). Selection moved to a
  separate `session/setModel` with the modern shape
  `{sessionId, model:{providerId, modelId, options?:{reasoningLevel}}, persistAsWorkspaceLastUsed:false}`.
  `runtimeModel` is NOT removed upstream — it is kept as the LEGACY retry payload.
  (3) `provider/updateAccountConfig` pushes an account snapshot
  `{revision, basedOnZCodeBuiltinRevision, providers, states}` with
  `revision = zcode-builtin:<rev>:<sha256 of the resolved builtin table PATH>`; without it every
  `account:*` model is rejected as "not in the Provider Registry".
  (4) `interaction/requestProviderRuntimeHeaders` is a server->client request issued before EVERY model
  request on an account provider; answer `{headersApplied: true, requestAuth: {apiKey}}`, else
  `{headersApplied: false, errorMessage}` which fails the turn with -32031 and retries forever.
  (5) NO version gating upstream — both paths are error-driven: modern setModel first, ONE fallback to
  legacy `runtimeModel` on any error; -32601 on `provider/updateAccountConfig` treated as benign no-op.
  Documented unknowns carried forward: the `-32602 Unrecognized key: runtimeModel` and
  `Select a model before continuing` strings are NOT documented upstream; the account-to-config provider
  id mapping and `AccountProviderPayload` shape were not quoted and 0.43.2 already changed the mapping.
  Those unknowns must be settled from the INSTALLED 3.12.x bundle (Mission 2), not from upstream.

## 2. Local ground truth on this machine
- item: Establish read-only local facts without touching user credentials or live sessions: installed ZCode desktop/CLI versions, the verified entry/app-bundle-relative path of the bundled provider config file, how the current adapter builds child env and the `runtimeModel` overlay, and the exact current failure signature (session start, yolo, prompt `Select a model before continuing`, setModel -32602 unrecognized `runtimeModel`). Capture as sanitized evidence.
- status: done
- dispatched: investigator subagent; output lands at `kaola-workflow/issue-79/evidence/02-local-ground-truth.md` in the main checkout
- result: `evidence/02-local-ground-truth.md`. Read-only; no tracked file touched, no session or process
  started, no credential file opened. Decisive facts from the INSTALLED build, which OVERRIDE upstream
  docs wherever they differ:
  - Desktop 3.12.3 (build 3.12.3.7463, `dev.zcode.app`); bundled CLI `--version` = 0.16.5 — the SAME
    string as the working 3.11.2 baseline, so a version-string gate cannot discriminate old from new.
  - `grep -c runtimeModel glm/zcode.cjs` = **0**. `runtimeModel` is GONE from the installed build, not
    merely schema-rejected. Upstream's "keep runtimeModel as a legacy fallback" does NOT describe 3.12.3.
  - The installed entry CANNOT locate its own bundled provider config: `qSo` probes only
    `dirname(entry)/provider/zcode-builtin.json` and `resolve(dirname(entry),"../../../../../config/provider/zcode-builtin.json")`.
    For the .app entry `/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs` the 5-up candidate
    resolves to `/config/provider/zcode-builtin.json`; the real file is ONE level up at
    `/Applications/ZCode.app/Contents/Resources/config/provider/zcode-builtin.json`. The 5-up path suits
    the source tree, not the shipped bundle. `main()` runs this before `run()` for `app-server`, so the
    child dies exit 1 — confirmed live 3x with the exact bundled error line.
  - Exactly two env names exist in the bundle: `ZCODE_BUILTIN_PROVIDER_CONFIG_FILE` and
    `ZCODE_PERSONAL_PROVIDER_CONFIG_FILE` (= `~/.zcode/v2/provider_config.json`). `Ohr` requires
    **both or neither**; with both set `$hr` passes them through verbatim and never probes. The adapter's
    `ENV_ALLOWLIST` forwards neither.
  - The bundled `zcode-builtin.json` is rules-only, revision 28, **0 secret literals**.
  - `session/create` and `session/resume` accept NO provider/baseURL/apiKey channel; `session/setModel`
    is `{sessionId, model:{providerId, modelId, options?:{reasoningLevel?}}, expectedRevision?, persistAsWorkspaceLastUsed?}`.
  - `"Select a model before continuing"` has ONE site, `createRuntimeModel`, thrown when the registry is
    empty at turn phase `model_creation`.
  - Root cause of the empty registry: app-server bootstrap omits the `standalone` option, so there is no
    credential store and the account source is the empty default. The host must push entitlement via
    `provider/updateAccountConfig` and auth via `interaction/requestProviderRuntimeHeaders`
    (params `{requestId, sessionId, turnId?, workspace, modelSelection, providerId, accountAccess?, reason}`,
    result `{headersApplied:true, requestAuth:{apiKey?, headers?}}`, 180 s timeout, mandatory for
    `access.type==="zhipu-account"`, and with NO not-implemented fallback — unlike
    `session/requestRuntimePreferences`). Failure is `-32031`.
  - Prior evidence confirms the regression boundary: desktop 3.11.2 accepted `runtimeModel` in live UAT;
    the 3.12.3 failures reproduce as `Unrecognized key: "runtimeModel"` and the
    `CONFIGURATION_ERROR / model_creation` turn failure.
  - Local registry state: only `builtin:bigmodel-coding-plan` enabled (GLM-5.3, GLM-5.3-Flash), plan cache
    `available`, both `zai` entries unauthenticated. The archived `KAOLA_ZCODE_NODE` path no longer exists;
    only `/opt/homebrew/bin/node`.
  - Could NOT establish (carried to Mission 2b): that the two env vars SUFFICE; the provider-instance shape
    `provider/updateAccountConfig` expects; the role of `~/.zcode/v2/provider_config.json` (0600,
    deliberately not opened).

## 2b. Registry-push and account-provider schema from the installed bundle
- item: Settle the one remaining blocking gap before implementation: the exact `provider/updateAccountConfig`
  params schema in the INSTALLED 3.12.3 bundle (the `providers` record value shape re-parsed by `$mr`, the
  `states[id].current` requirement in `G6n`, exact key casing of `revision` / `basedOnZCodeBuiltinRevision`,
  and how the installed side VALIDATES the revision string), plus the account-provider id and model-id
  mapping that `session/setModel` expects versus the desktop registry id `builtin:bigmodel-coding-plan`,
  and confirmation of the runtime-headers result schema. Read-only bundle inspection; no process start.
- status: done
- dispatched: investigator subagent; output lands at `kaola-workflow/issue-79/evidence/03-registry-push-schema.md`
  in the main checkout
- result: `evidence/03-registry-push-schema.md`. The subagent completed 72 bundle extractions but its
  session ended before it wrote the report, and it was no longer reachable to resume. Nothing was
  re-investigated: the findings were recovered verbatim from that agent's own recorded tool results
  and landed as run evidence. Settled facts:
  - `session/setModel` must receive `providerId = "account:bigmodel-individual-coding-plan"` (NOT the
    desktop registry id `builtin:bigmodel-coding-plan`) and `modelId = "GLM-5.3"` / `"GLM-5.3-Flash"`.
    Selection schema `mo = {providerId, modelId, options?:{reasoningLevel?}}` all `.strict()`.
  - `provider/updateAccountConfig` EXISTS in 3.12.3 (one of only two `provider/*` methods). Validator
    `G6n` requires non-empty `revision` and `basedOnZCodeBuiltinRevision` (capital Z and C -- upstream's
    lowercase spelling is wrong for this build), a `providers` record whose values are parsed down to
    `{builtinModelIds, access:{type, entitled}}`, and a REQUIRED boolean `states[id].current` for every
    entitled zhipu-account provider.
  - The builtin revision string is `zcode-builtin:<rev>:<sha256 of the RESOLVED PATH STRING>` -- the hash
    is over the path, not the file content (`Fy` / `TSo`). Three candidate values measured on this machine.
  - `interaction/requestProviderRuntimeHeaders` answer is `{headersApplied:true, requestAuth:{apiKey}}`;
    `requestAuth` is required in that branch and all objects are `.strict()`. Mandatory for
    zhipu-account providers, with no not-implemented fallback.
  - Ordering: the snapshot is per app-server PROCESS (`parseProcessAccountProviderConfigSnapshot`,
    `startProcessProviderRegistryRuntime`), so push once per backend, then create / setModel / subscribe / send.
  - NOT ESTABLISHED, and explicitly carried into Mission 5 rather than guessed: which of the three
    `basedOnZCodeBuiltinRevision` candidates the app-server expects (i.e. whether the active path
    becomes our injected bundled path or a version-keyed runtime copy), and whether the env injection
    SUFFICES for app-server start. Both are live-only questions.

## 3. Minimal production adapter change
- item: Implement in `scripts/kaola-zcode-acp.py` only the required 3.12+ compatibility: resolve the bundled provider-config path from the verified ZCode entry/app bundle (never an inherited/stale path) and pass it via the documented env var(s); emit the current provider-snapshot/model-selection shape on create/resume/setModel while retaining the tested older shape where feasible; answer `interaction/requestProviderRuntimeHeaders`. Preserve the one-enabled-Coding-Plan-provider policy, fail-closed refusals, and redaction. Regenerate any generated surface through `./scripts/render-skills.py --write`.
- status: done
- dispatched: self (inline), worktree `.kw/worktrees/issue-79`, branch `workflow/issue-79`
- result: four commits — `2680672`, `f5bb7dd`, `30ebae4`, `06b8459`. Additive: across the whole
  candidate only 13 production lines were deleted; no pre-3.12 semantics changed and no provider added.
  - Env: `BUILTIN_PROVIDER_CONFIG_ENV` / `PERSONAL_PROVIDER_CONFIG_ENV`,
    `BUILTIN_PROVIDER_CONFIG_CANDIDATES`, `resolve_builtin_provider_config()`,
    `personal_provider_config_path()`. `build_child_env()` takes the verified entry and sets BOTH
    names or NEITHER; `ZCodeBackend.start()` passes `self.entry`. Neither name is in `ENV_ALLOWLIST`,
    so an inherited value is dropped before the derived one is set. Verified against the real install:
    the `.app` entry resolves to `<Resources>/config/provider/zcode-builtin.json`, the candidate the
    CLI's own probe misses.
  - Registry: `ACCOUNT_PROVIDER_BY_CODING_PLAN`, `read_builtin_release()`,
    `builtin_revision_string()` (sha256 of the resolved PATH, not the bytes), `account_model_ids()`,
    `account_reasoning_levels()`, `build_account_config()`; `resolve_account()` and
    `push_account_config()` (tolerating -32601 from a pre-3.12 backend as a benign no-op).
  - Selection: `create_backend_session()` creates with no model channel and falls back to the legacy
    `runtimeModel` overlay ONLY on the backend's own `Model config is missing` error -- the CLI
    version string is 0.16.5 on both builds and cannot discriminate. `select_account_model()` sends
    the `account:*` provider with an explicit `options.reasoningLevel` and
    `persistAsWorkspaceLastUsed: false`.
  - Callback: `runtime_headers_answer()` replaced the previous `{}` reply, which could not satisfy the
    strict response union and failed every 3.12+ turn. It answers
    `{headersApplied: true, requestAuth: {apiKey}}` for the one authorized provider and
    `{headersApplied: false, errorMessage}` for anything else.
  - Mid-session switch (`06b8459`, found during self-review of the candidate and confirmed by the
    outer review): `session/set_config_option` with `configId: model` still sent `runtimeModel` and no
    reasoning level, so an Agent switching model mid-session on 3.12+ hit
    `Unrecognized key: "runtimeModel"` even after the initial selection worked. It now takes the same
    account path, keeping the overlay only for a pre-3.12 backend, with the one-Coding-Plan refusal
    unchanged.
  - Generated surfaces regenerated through `./scripts/render-skills.py --write`; `--check` PASS,
    budgets OK. `platforms/zcode.yaml` edited at the template source, never `skills/` by hand.
  - One regression introduced and fixed inside this mission (`30ebae4`): a comment spelled the CLI's
    five-levels-up probe path literally, and the renderer copied it into the generated package, which
    `test-generated-skills.py` rejects because a Skill package must contain no `../`. Reworded; that
    acceptance is PASS again.

## 4. Focused hermetic tests
- item: Extend the hermetic contract suite (`tests/contract/fake-zcode-app-server.py`, `tests/contract/test-zcode-acp-contract.py`) to cover old-shape and new-shape backends, bundled provider-config path resolution failure, runtime-header request handling, secret redaction, and missing/absent credentials. Tests must carry no real secret and must fail against the pre-change adapter for the new-shape cases.
- status: done
- dispatched: self (inline)
- result: two new files rather than edits to the existing 706-line fake, so the tested legacy contract
  stays intact:
  - `tests/contract/fake-zcode-312-app-server.py` — a 3.12.3-shaped hermetic backend: `session/create`
    strict with no model channel (a `runtimeModel` overlay draws the real -32602 `Unrecognized key`),
    `provider/updateAccountConfig` validated like `G6n` PLUS the live-measured `availability` and
    `entitled` requirements, `session/setModel` validated like `mo` and refusing both an unregistered
    provider and a selection with no reasoning level, an empty registry failing the turn with
    `CONFIGURATION_ERROR` / `Select a model before continuing` at phase `model_creation`, and a
    per-model-request runtime-headers callback checked against the strict union.
  - `tests/contract/test-issue-79-zcode-312.py` — 18 cases covering candidate resolution order
    (including the shipped `.app` layout the CLI's probe misses), both-or-neither env, the inherited
    poisoned value never reaching the child, create-without-model then setModel, the account
    snapshot's exact keys and casing, the revision hashing the PATH not the bytes, reasoning-level
    resolution against rule ordering, the headers callback answered and the turn completing, the
    mid-session model switch, the credential absent from every ACP and log byte, refusal of a model
    the plan does not offer, refusal to hand the key to a foreign provider, two fail-closed cases
    (absent registry, empty credential), and a pre-3.12 backend still driven through the legacy overlay.
  - Baseline proof: against the pre-change adapter (`f6be8a3`) 11 of the then-15 cases failed
    (7 errors + 4 failures); the 4 that passed are deliberately the back-compat and redaction guards
    that must hold on both. Candidate restored and re-verified afterwards.
  - The two mid-session cases were written failure-first: the switch case reproduced the exact
    `Invalid params - (root): Unrecognized key: "runtimeModel"` before `06b8459` and passes after;
    the foreign-provider guard passes both before and after, by design.
  - No real secret anywhere: the only key is the fixture value already inside `tests/`.
  - Registered in `scripts/validate.sh` (`python_suites_all` + lane a).

## 5. Live verification with the real installed ZCode
- item: In a disposable isolated Git repo (not this repo, not any user project), drive the real installed ZCode through the Runner ACP path: start with yolo applied, explicit correct model selection, one simple live model reply, then exact stop with `residual[]`. Redact every secret. If a boundary genuinely blocks the live turn, record the exact blocker honestly; a fake-backend pass may not stand in for it.
- status: done
- dispatched: self (inline), isolated disposable repo `/tmp/kpr-i79-live-08jK6H/repo`
- result: `evidence/04-live-3123-verification.md`. **The live turn succeeded on real ZCode 3.12.3.**
  Through the Runner ACP path (`kaola-tmux.sh zcode start/send/stop`):
  - `start`: `state: ready`, mode **yolo applied: true**, no error.
  - `send` "Reply with exactly the word: KAOLA79OK": `final_text: "KAOLA79OK"`,
    `stop_reason: end_turn`, `outcome: turn_completed`, 4530 ms, 0 tool calls, 0 files changed.
  - `stop`: `stopped: true`, **`residual_pids: []`** — as on all three stops in this mission.
  The live run settled the two questions Mission 2b flagged as statically unresolvable, and corrected
  the implementation twice rather than guessing:
  1. `states[<id>]` needs `availability` (enum) and `entitled` as well as `current`; the snapshot
     validator `G6n` reads only `current`, so static reading understated the wire schema.
  2. `session/setModel` refuses a Coding Plan selection with no explicit `options.reasoningLevel`;
     levels now come from the bundled table's `modelConfigRules` rule ordering.
  The highest-risk open item, `basedOnZCodeBuiltinRevision`, needed no guess: computing
  `zcode-builtin:<rev>:<sha256 of the resolved injected path>` was accepted live.
  Secret handling: credential read in memory only; `credentials.json`, `setting.json` and
  `provider_config.json` never opened; leak check over every receipt plus the event log returned
  **False**; nothing written under `~/.zcode`; `persistAsWorkspaceLastUsed: false`.
  Cleanup: no leftover session or holder. Pre-existing orphans belonging to the #74 and #67 runs were
  observed and deliberately left alone; the one hung process this run created (a bare `kaola-tmux.sh`
  waiting on stdin) was killed by exact PID after confirming ownership.
  Not re-run after `06b8459`: that commit changes only the mid-session switch path, which the live
  run did not exercise, and it is covered failure-first by the hermetic suite. Stated so the outer
  review can decide whether it wants a second live pass.

## 6. Full validation and frozen candidate for outer review
- item: Run `./scripts/render-skills.py --check` and `./scripts/validate.sh` (coordinating shared validation load with the #78 run), record exact outcomes, then freeze the candidate commit SHA and diff plus sanitized raw verification evidence under `kaola-workflow/issue-79/evidence/` and report for outer review. Stop there; no finalize/archive/sink.
- status: done
- dispatched: self (inline). Raw receipts in `kaola-workflow/issue-79/evidence/`
- result: `evidence/08-final-candidate.md` (+ `06-suite-sweep-06b8459.txt`, `07-candidate.diff`).
  Final candidate **`55f330fb99a57338c949c953d7c7e98327c603f2`**, 5 commits, rebased cleanly onto
  `main` @ `f6cbe27` so the branch inherits #78's here-document fix (here-docs in
  `scripts/kaola-tmux.sh`: 9 at the old base, 0 now).
  - Two review-driven fixes landed failure-first: `e3477ea` (mid-session switch routed through the
    account path) and `55f330f` (selection committed to local state only after the backend accepts).
  - Re-verified on this candidate: `render --check` PASS, generated Skills PASS,
    `test-issue-79-zcode-312.py` 19/19, `test-zcode-acp-contract.py` 34/34, zcode host and heartbeat
    exit 0, `test-issue-51-runner-integration.py` **6/6** (was 4/6 on the old base — its timeouts were
    #78's deadlock, never this candidate), inherited `test-issue-78-heredoc-deadlock.py` 3/3.
  - Second live run on THIS candidate, fresh isolated repo, real desktop 3.12.3: start `state: ready`
    with yolo applied, `final_text: "KAOLA79FINAL"`, `stop_reason: end_turn`, 5463 ms, then
    `stopped: true` with **`residual_pids: []`**. Credential absent from all receipts; no leftovers.
  - **Not green overall, stated plainly:** `test-issue-49-grok-bot-host.py` remains RED
    (`[Errno 66]` teardown race, reproduced identically at the original base, owned by **#80**), so
    `validate.sh` still exits non-zero. No claim of a full green validate is made.
  - Awaiting outer ACCEPT. No finalize, archive, sink, issue close, release, or global install.
