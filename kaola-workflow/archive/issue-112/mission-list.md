# Upgrade the OpenCode adapter for OpenCode V2 (2.0.11)

Issue: #112 (bug, enhancement) — only open issue. Branch `workflow/issue-112`,
worktree `/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-112`.
Main root `/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner` at 7fc6fe3 (#111 merged
and archived, so the SKILL.md headroom contention in the issue body is resolved).

Host-set order of work supersedes any V1-shaped assumption in the issue notes: web research on the
V2 ACP rewrite comes FIRST; the Pink 1.18.31 pin is reference-only; the target is V2 exclusively.
Implementation seat only — do NOT self-finalize, merge, or close #112 before Host acceptance.
Irreversible/value-laden calls (notably `opencode auth login`) print HUMAN_DECISION_REQUIRED and wait.

---

## 1. Research OpenCode V2's rewritten ACP against upstream sources
item: Web-research the V2 ACP surface before touching code — opencode.ai changelog, the V2 migration
  guide (opencode.ai/v2/docs/migrate-v1), opencode-ai/opencode releases and issues. Target questions:
  what changed in ACP between V1 and V2; the status of the `session/new` -> `ClientError` defect
  (open? fixed in which version? workaround?); the `opencode serve --stdio` 401 / server-password
  auth model; whether `opencode acp` is still the supported entrypoint; the V2 `mini` launch shape.
  Record sources with dates and mark unknowns explicitly. Do not force the V1 ACP shape onto V2.
status: done
dispatched: self (inline, WebSearch/WebFetch/gh api) -> kaola-workflow/issue-112/research-v2-acp.md
result: kaola-workflow/issue-112/research-v2-acp.md (7.4 KB, R1-R7 + unknowns). Headline: the
  upstream tracker is anomalyco/opencode, and **#35457 "Port ACP support to V2 core and APIs" is
  OPEN at priority Low** — `opencode acp` on the V2 line is still a legacy-compat shim
  (`acp/service.ts` on `@opencode-ai/sdk/v2` compatibility `sdk.session.*` routes), never ported to
  V2 session semantics. Corroborated by /v2/docs/acp -> 404 and by GitHub Releases carrying no v2
  entries at all (v1.18.31 is still "Latest"; v2.0.10/v2.0.11 are bare tags). #50236 independently
  reports ACP session/new broken on exactly 2.0.4/2.0.6/2.0.11 (works on 2.0.3). V2 `serve` 401 is
  by design (#49452, #45856, #31254) so the 401 in the issue body is expected behaviour, not the
  defect. The wedged managed service is upstream #41696, OPEN, same port 49374, remedy mutates user
  config. Two probes fall out for Mission 2: rule out http_proxy (#31096) and read the swallowed
  cause from ~/.local/share/opencode/logs (#17285) / `acp --print-logs` (#31091). Also: `--mini` was
  a HIDDEN flag (#41513), so `--help` omitting it proves nothing — must be settled by executing.

## 2. Reconcile research against this machine's live opencode v2.0.11
item: Read-only probes only, reusing the issue's recorded probe history rather than redoing it
  blindly. Confirm/refute each upstream claim locally: version string, `opencode acp` initialize
  shape, session-method failure, the spawned `serve --stdio` child's env and 401, the `mini`
  subcommand surface, and the wedged managed service. Where research or live evidence contradicts
  #112's design notes, correct them by commenting on the issue.
status: done
dispatched: self (inline, read-only probes) -> /tmp/kpr112/*.json receipts; correcting comment on #112
result: **The blocker is resolved, and the issue's leading hypothesis is refuted.** Root cause is a
  single environment fact: HTTP_PROXY/HTTPS_PROXY are set on this machine with **no NO_PROXY**, so
  OpenCode V2's loopback HTTP hop to its own server is sent to the forward proxy. Clean A/B, same
  shell, only NO_PROXY=127.0.0.1,localhost differing:
    opencode acp session/new : ClientError  ->  ses_f3e7a335cffecFBdIiffLs7KmO
    opencode service status  : "stopped"    ->  http://127.0.0.1:49374
    opencode models          : timeout 40s  ->  exit 0
    opencode auth list       : timeout 40s  ->  exit 0
  So the "wedged managed service" (#112 section 4) was never wedged, and the 401 in the intake was
  the proxy answering, not OpenCode's server (V2 serve auth is always-on BY DESIGN per upstream
  #49452/#45856 -- expected, not the defect). Upstream #31096 fixed exactly this class on the V1
  line; per #35457 the V2 ACP adapter was copied rather than ported, so it regressed.
  FULL ACP ROUND TRIP ACHIEVED on 2.0.11 (AC#1 strong branch): initialize -> session/new ->
  session/set_config_option -> session/prompt (stopReason end_turn, shell tool ran, agent replied
  ROUNDTRIP_OK) -> session/close {}. session/list also works.
  Corrections to #112's design notes (all live-measured): (a) acp_effort_config_id "effort" is NOT
  obsolete -- it is present on V2 with options low/high/max/default, and acp_model_config_id "model"
  works via session/set_config_option; (b) `--mini` is genuinely REMOVED, not hidden -- "Unrecognized
  flag: --mini in command opencode"; (c) top-level --model and --variant are ALSO rejected, which the
  issue missed; (d) OPENCODE_CONFIG_CONTENT is ignored for model selection on 2.0.11 in every shape
  (V1 agent.build, V2 agents.build, top-level model) and on every path (acp/run/models) -- upstream
  #50236, which names 2.0.11 exactly; (e) acp_init_meta is what the CLIENT sends as
  clientCapabilities._meta, so the agent-advertised opencode/child-session-updates does not belong
  there; (f) the live ACP default model is opencode/deepseek-v4.1-flash, not opencode-go/....
  AC#4 measured: session/request_permission IS used on V2 (out-of-cwd edit) with exactly three
  choices -- allow_once / allow_always / reject_once, no skip-all, no _meta; configOptions carries
  only model/effort/mode. In-cwd shell/execute under default build mode ran with NO permission
  request, re-verified under an isolated empty config so it is a V2 default, not the user's config.

## 3. Land the V2 adapter + manifest change
item: platforms/opencode.yaml carries only live-verified V2 values (version pin, acp_quirks stating
  the MEASURED permission/skip-all position or an evidenced unverified record, env allowlist,
  launch/steering summaries, effort model); scripts/adapters/opencode.sh launches on 2.0.11 with no
  top-level `--mini` and no bare `--variant`; the `opencode acp` session blocker is resolved or
  evidence-re-pointed. Regenerate via ./scripts/render-skills.py --write. Diff stays scoped to
  OpenCode surfaces; skills/ and hosts/ only via the renderer; templates/grok-golden/ frozen.
status: done
dispatched: self (inline) -> platforms/opencode.yaml, scripts/adapters/opencode.sh, regenerated skills/
result: launch is now ("$launch_repo" --auto); --model/--variant dropped from argv because V2 rejects
  them; adapter_prepare_model_environment rewritten to the V2 config shape (agents.build.model with
  the variant folded in after "#", per the official migrate-v1 guide) with the measured fact that
  2.0.11 ignores it recorded in-comment; adapter_preflight now reports loopback=direct|excluded|proxied
  as EVIDENCE ONLY, never a gate. Manifest: acp_verified_versions cli=2.0.11;protocol=1, acp_quirks
  rewritten to the measured V2 position, acp_env_allowlist gains NO_PROXY, launch_summary drops
  --mini, steering_summary re-pointed 1.18.29 -> 2.0.11 keeping 1.18.17 as history. Decision (kept
  deliberately conservative for a minimal patch release): the Runner DECLARES and REPORTS the loopback
  requirement, it does not silently rewrite the operator's proxy env; no classifier, retry or waiting
  layer was added, per the project contract.

## 4. Update the contract tests to V2 truth
item: Start from tests/contract/test-issue-24-opencode-pty-bypass.py and
  test-issue-88-permission-defaults.py; sweep the lighter references listed in the issue. No test may
  assert a V1-only string as current truth.
status: done
dispatched: self (inline) -> tests/contract/, docs/api.md
result: test-issue-24 (SKIP_ARGV loses --mini; pins <repo> --auto; new test forbids --mini/--model/
  --variant in the launch argv), test-issue-88 (new test pins the measured V2 choice set and
  cli=2.0.11; steering calibration re-pointed), test-issue-22, test-adapters.sh, docs/api.md.
  All three python suites pass: 15, 42, 23 tests OK.

## 5. Static verification
item: ./scripts/render-skills.py --check passes with every templates/budgets.json budget holding, and
  ./scripts/validate.sh passes in the FOREGROUND under
  `env -u KAOLA_ZCODE_ENTRY -u KAOLA_ZCODE_NODE -u KAOLA_ACP_DISPATCHER`; trust the log EXIT= line.
  Record the exact outcome.
status: done
dispatched: self (inline, foreground) -> /tmp/kpr112/validate-112{,b,c}.log
result: render-skills.py --check PASS, budgets OK. SKILL.md unchanged at 12090/12288 B because every
  field touched renders into references (acp.md 5579, platform.md 4242, steering.md 6519, all under
  8192), so the #111 headroom contention never bound.
  validate.sh run 1 (validate-112.log): rc=1, one failure --
  test-issue-73-canonical-root.py test_acp_start_under_a_dispatcher_passes_the_shell_to_the_acp_resolver
  got heartbeat-host-conflict instead of heartbeat-host-unresolved. NOT the diff: KAOLA_ACP_HEARTBEAT_HOST
  and KAOLA_ACP_HEARTBEAT_HOST_SOCKET leak in from the dispatching ZCode Host (extends the known
  KAOLA_ZCODE_ENTRY/NODE leak to two more names).
  validate.sh run 2 (validate-112b.log), env -u on all five names: rc=0, zero FAIL lines.
  validate.sh run 3 (validate-112c.log), re-run after the TUI-chrome fix invalidated run 2's PASS
  evidence: **rc=0, zero FAIL lines** -- this is the final tree's outcome.
  Note: this validate.sh emits no EXIT= line, so the process exit code is the authority.

## 6. Live V2 smoke through the Runner
item: start -> observe -> send -> capture -> stop on an exact owned tmux session against
  opencode v2.0.11, receipts recorded, session stopped cleanly. Never touch foreign sessions
  (kaola-ae2f524c, kaola-val.*).
status: done
dispatched: self (inline) -> /tmp/kpr112/smoke-*.json, /tmp/kpr112/pane.txt
result: session i112-smoke on scratch repo /tmp/kpr112/smokerepo, PTY transport.
  start   -> "started"; child_process = /opt/homebrew/bin/opencode /private/tmp/kpr112/smokerepo --auto
             (exactly the new launch line; the V1 line would have exited 1)
  observe -> "observed", relay managed=true; TUI live showing 2.0.11 / "Build auto"
  send    -> "sent", payload_fingerprint sha256:fd27bb23cbde...
  capture -> agent reply "I112_PTY_OK" visible within ~8 s
  stop    -> "stopped"; tmux ls afterwards shows only the foreign kaola-ae2f524c, untouched.
  The smoke EXPOSED A REAL REGRESSION the static tests could not: activity_hint came back "unknown"
  on a live idle pane because the V2 footer reads "ctrl+p commands" while the adapter matched
  "ctrl+p cmd" -- and "cmd" is not a substring of "commands". Fixed in adapter_detect_tui and
  adapter_activity_hint, re-rendered, re-observed live -> "idle", and validate.sh re-run (run 3).

## 7. Readiness handback to the Host
item: Establish readiness only — research findings vs live facts, diff stat, exact verification
  outcomes, run locator. Finalization, issue closure, archive, and sink are NOT missions and belong
  to the Host / Workflow finalize.
status: done
dispatched: self (inline) -> issue comment + this file
result: correcting comment posted to #112
  (https://github.com/KaolaBrother/kaola-project-runner/issues/112#issuecomment-5754404909);
  CHANGELOG 0.5.5 entry added; committed as 34c0e5c on workflow/issue-112, UNPUSHED and NOT merged.
  Readiness only -- the Host owns acceptance, and finalize/closure/archive/sink are not missions.
  Open judgment call flagged for the Host: the Runner reports the loopback-proxy requirement but
  does not inject NO_PROXY into the child env, so on a proxied machine the operator must exclude
  loopback themselves. HUMAN_DECISION_REQUIRED was never reached -- `opencode auth login` proved
  unnecessary once the proxy was identified, so no user credential was touched.

## 8. Host round 2: inject a child-scoped loopback bypass and prove the ACP transport live
item: Host ruling on judgment item 1 is to inject, not just report. The opencode child alone gets
  the missing 127.0.0.1/localhost appended to NO_PROXY/no_proxy when a forward proxy is set and those
  entries are missing; the operator env is never touched and existing entries are never removed or
  reordered. State whether the PTY child shares the path. Preflight reports what the child actually
  sees. Add a unit contract test with no live dependency. Run the full ACP round trip through the
  Runner on session opencode-KPR-i112-acpsmoke with the default transport (start/observe/send/
  capture/stop). Settle the configOptions and stopReason residuals against the manifest. Re-run
  render --check and validate.sh in the foreground. Item 2 (preflight keys) stays out of scope.
status: done
dispatched: self (inline) -> same branch workflow/issue-112; receipts in /tmp/kpr112/r2-*
result: commit 9708980 (19 files, +708/-47; most of it is kaola-acp.py vendored x11).
  PTY shares the exposure, measured on a private tmux socket: a Runner-started tmux server inherits
  the proxy, and the V2 TUI hung at "Starting background server..."; the existing shared server
  carries no proxy. So both children are covered: ACP via kaola-acp.py agent_environment()
  (LOOPBACK_NO_PROXY_PLATFORMS={"opencode"}), PTY via the adapter's -e channel.
  Live with caller NO_PROXY unset: ACP session opencode-KPR-i112-acpsmoke ses_f3e409afeffePgjzfTWuwo8peK,
  send -> turn_completed/end_turn/"I112_ACP_OK", capture shows it, stop -> stopped, exit 0, no
  residual pids. The first start's turn failed with provider.no-route on the native default
  opencode/deepseek-v4.1-flash (#50236 fallback); the restart used --model/--effort.
  configOptions model/effort/mode confirm the manifest unchanged. PTY fresh-server re-proof: TUI up.
  render --check PASS with budgets; validate.sh (four Host names stripped) rc=0, 0 FAIL lines.
  Issue comment: #issuecomment-5754600824.
