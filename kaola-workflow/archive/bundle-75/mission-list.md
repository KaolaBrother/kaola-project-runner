# Issue #75 — Codex/ZCode host compact recovery + Project Runner doc boundary

Run: bundle-75, branch workflow/bundle-75, worktree .kw/worktrees/bundle-75.
Scope: Codex + ZCode host agents using Project Runner / Kaola-Delegator only.
Excluded: Grok Bot, other native hosts (future principles only), generic entry (no hooks).
#74 dependency: read-only — final name kaola-delegator/kaola-delegator, candidate unmerged
(6e5c333, docs freeze 380ca2b). Do not touch its templates; rebase-safe-point integration later.
Acceptance requires: evidence matrix, isolated real-compact proof per host, doc-boundary
three-scenario coverage, render --check + validate.sh PASS, frozen SHA for outer review.
No finalize/push/close without ACCEPT.

## item
Capability evidence matrix: Codex SessionStart(compact) verified path; ZCode 0.16.5 hook
sources (user cli/config.json hooks.enabled vs plugin hooks.json vs ignored project hooks),
session-start snapshot, SessionStart(compact) trigger reality (binary: sessionStartHookRan
once-per-session, only startup/resume call sites), app-server exited diagnosis
(provider-config lookup fails for glm/zcode.cjs entrypoint; env fixes ZCODE_STORAGE_DIR /
ZCODE_DATA_BASE_DIR / ZCODE_BUILTIN_PROVIDER_CONFIG_FILE; 3.12.3 rejects runtimeModel,
model:{providerId,modelId} + account credential store is the new path).
status: done
dispatched: self; output lands in kaola-workflow/bundle-75/evidence/capability-matrix.md
result: kaola-workflow/bundle-75/evidence/capability-matrix.md — resumed worker
reconciled the stopped dispatch: Codex path fully verified (0.153.4 binary enum
startup/resume/clear/compact, merge-across-layers, trust + bypass flag, local
kaola-workflow precedent); ZCode 0.16.5 binary-verified: runSessionStartHooks has
only startup/resume call sites (SessionStart(compact) cannot fire), runtimeModel
absent, model:{providerId,modelId} path, env levers present, workspace hooks
discovered but admission-gated; live ZCode proof blocked on #79.

## item
Isolated real ZCode verification: reproduce/diagnose app-server exited; isolated
ZCODE_STORAGE_DIR carrier; session/create with model field vs account provider; hooks fire
on startup; real /compact — does SessionStart(compact) fire + additionalContext reach model
before next reasoning; UserPromptSubmit/resume fallback behavior.
status: blocked
result: BLOCKED — outer assignment explicitly prohibits ZCode model/Hook live work and
any credential access; additionally #79 owns the adapter fix that makes the ZCode
environment usable (app-server exited remains unreproduced by an authorized owner).
Static bundle facts are recorded in evidence/capability-matrix.md. Remains blocked on
#79 until its adapter lands and live verification is authorized.

## item
Codex compact-recovery deliverable: short Runner-owned recovery payload + merge-safe
install/uninstall into ${CODEX_HOME}/hooks.json (own entry only, foreign/Workflow hooks
untouched) + isolated verification (real compact if the local Codex build supports it).
status: done
dispatched: self; output lands in templates/codex-host/compact-recovery.md +
scripts/kaola-codex-compact-hook.py + tests/contract/test-issue-75-codex-compact-hook.py
+ docs/codex-host.md on branch workflow/bundle-75; live-compact proof lands in
kaola-workflow/bundle-75/evidence/
result: shipped at d727e1f — one owned entry kaola-project-runner:compact-context in
${CODEX_HOME}/hooks.json, payload under <codex_home>/kaola-project-runner/hooks/,
foreign/Workflow hooks preserved byte-for-byte, malformed config refused, idempotent
install/status/uninstall. Real /compact proof in evidence/codex-compact-live/:
SessionStart(compact) fired, payload reached the model before next turn, Workflow
hook fired alongside; session exact-stopped with residual_pids=[].

## item
ZCode carrier deliverable per verification findings (plugin hooks.json and/or
cli/config.json entry merge-safe; Runner-spawned host injection path if needed);
heartbeat/event prompt must instruct Skill reload for normal wait/wake coverage.
status: blocked
result: BLOCKED — not shipped, and not shippable on current evidence: ZCode 0.16.5
binary has only startup/resume runSessionStartHooks call sites (SessionStart(compact)
cannot fire), so no verified native compact carrier exists to install. Live
verification of any alternative (plugin hooks.json, cli/config.json events,
UserPromptSubmit fallback) is prohibited by outer ownership and blocked on #79.
See evidence/capability-matrix.md for the binary-verified facts.

## item
Project Runner documentation-maintenance boundary in templates/orchestrator (+ reference if
needed, within budgets): dispatch doc-impact judgment; acceptance via Workflow docking (no
second ledger/gate); AGENTS.md rules per ADR 0023 (verified durable facts, stricter local
constraints, no quota/session/issue history, owner-authored rewrite needs owner auth);
post-finalize doc verification + safe-point in-flight sync (no per-beat full scan).
status: done
dispatched: self; output lands in templates/orchestrator/references/doc-maintenance.md
+ a budget-fit pointer in templates/orchestrator/SKILL.md.tmpl (generated
skills/kaola-project-runner/ via render-skills.py --write)
result: shipped at d727e1f — substantive policy in generated
skills/kaola-project-runner/references/doc-maintenance.md (2501 B, within 8192 B
budget): dispatch-time doc-impact judgment naming ownership; acceptance reuses the
Workflow documentation docking (no second ledger/gate); AGENTS.md carries only
verified durable facts + stricter local constraints (no machine-global copies,
quota/session/issue history); owner-authored instruction rewrites need owner
authorization; post-sink verification covers target branch/remote/Issue/docs
docking/cleanup; in-flight Agents sync at a safe point; heartbeat tracks duties
without per-beat doc scans; keyword presence never substitutes for judgment.
Main SKILL.md carries only the pointer (17392 B vs 17408 B budget).

## item
Contract tests for new deliverables (merge safety, payload, generated surfaces) +
render --check + validate.sh.
status: done
result: tests/contract/test-issue-75-codex-compact-hook.py 10/10 PASS (install,
idempotency, foreign-hook preservation, malformed refusal, uninstall, payload
content, generated doc-maintenance surfaces, byte budgets); registered in
scripts/validate.sh lane B. render-skills --check PASS on d727e1f.
validate.sh PASS on the post-#78 base (f6cbe27) — all lanes completed,
kaola-grok-bot-verify PASS, git diff --check clean, sweep residual_pids=[].
Two unrelated pre-existing flakes were A/B-proven on the base: (a) the earlier
test-issue-50 PTY timeout was the Issue #78 heredoc deadlock — fixed by
rebasing onto #78's landed fix; (b) test-issue-49-grok-bot-host.py hits a
detached git gc --auto (gc.autoDetach) racing fixture rmtree on repo/.git —
reproduces identically on main f6cbe27 without the #75 diff; full gate ran
green with env-only GIT_CONFIG gc.autoDetach=false, no repo changes.

## item
Freeze candidate SHA; raw evidence pack (hook input/output, model behavior, command
receipts) in kaola-workflow/bundle-75/evidence/; report to outer review.
status: done
result: candidate frozen at d727e1f (workflow/bundle-75, rebased onto f6cbe27
post-#78 main; 12 files, +737/-27). Evidence pack: evidence/capability-matrix.md,
evidence/codex-compact-live/ (FINDINGS.md, post-compact pane, sanitized rollout
extracts, installer receipts), evidence/validation-receipts.md (post-rebase
render --check + validate.sh receipts incl. pre-existing flake A/B). Report
delivered to outer review; awaits outer ACCEPT before any finalize/archive/sink.

## item
ZCode compact-recovery follow-on (new authorization + #79 compatibility, appended
after outer review of d727e1f): (1) statically verify the minimal executable
post-compact hook/recovery trigger in ZCode 3.12.3 — if SessionStart(compact)
truly cannot fire, identify an equivalent safe entry inside the existing hook
sources (user cli/config.json hooks.enabled, plugin hooks/hooks.json, or the
next model-visible prompt path) without building a new scheduler; (2) after #79
lands on main, run an isolated real compact in a scratch repo and capture
evidence the model reads the recovery instruction after compaction.
status: blocked
dispatched: self; static findings land in
kaola-workflow/bundle-75/evidence/zcode-compact-mechanism.md; live evidence
lands in kaola-workflow/bundle-75/evidence/zcode-compact-live/ once #79 merges
to main. Constraints: no credential read/copy/decrypt/output, no global
install/config changes, no touching #79 worktree or other sessions; Codex
side stays frozen at d727e1f.
result: BLOCKED at phase 2 — phase 1 complete in
evidence/zcode-compact-mechanism.md: ZCode 0.16.5 hook enum verified complete
(SessionStart/UserPromptSubmit/PreToolUse/PermissionRequest/PostToolUse/
PostToolUseFailure/Stop; no compact event exists); SessionStart(compact)
cannot fire (startup/resume call sites only, once-per-session flag).
Recommended minimal entry: send-path recovery carrier — read-only
compaction cursor on the part table (covers manual /compact AND auto
context-pressure compaction) + KPR carrier prepended to the next Runner
prompt; zero ZCode config mutation. Documented alternative: UserPromptSubmit
hook in cli/config.json (covers non-Runner prompts; costs user-global write
+ per-prompt process). Live phase waits on #79 merging to main, then runs
the isolated real-compact evidence in evidence/zcode-compact-live/.

## item
Outer-review fix round on d727e1f: (a) hook_entry builds the command as
cat "{path}" — a CODEX_HOME containing $(), double quotes, or other shell
metacharacters would be interpreted at hook execution; switch to minimal
safe quoting (shlex.quote) and behavior-test with a metachar isolated path
proving read-only. (b) backup.write_bytes inherits umask (0644) for the
prior hooks.json content — switch to atomic 0600 write and test the mode.
(c) "byte-for-byte" wording is wrong — entries are preserved as JSON while
the file is re-serialized; correct the phrasing in script docstring,
docs/codex-host.md, CHANGELOG.md, test docstrings, and evidence. No real
CODEX_HOME is touched. Re-run render --check, the i75 suite, and full
validate.sh honestly, then freeze a new SHA for outer review.
status: done
dispatched: self; fixes land on workflow/bundle-75 in
scripts/kaola-codex-compact-hook.py + tests/contract/test-issue-75-codex-
compact-hook.py + docs/codex-host.md + CHANGELOG.md; receipts in
kaola-workflow/bundle-75/evidence/validation-receipts.md
result: done at 78a0dfe — command now `cat {shlex.quote(path)}`; backup uses
the shared atomic writer at 0600 via write_backup(); "byte-for-byte"
replaced with the accurate JSON-content/re-serialized wording in script
docstring, docs/codex-host.md, CHANGELOG.md, test docstring, evidence.
Suite 12/12 PASS incl. new live `sh -c` metachar-home test (no side effects,
payload stdout only) and backup-mode test. render --check PASS; validate.sh
PASS (same env-only gc.autoDetach mitigation for the pre-existing #49 base
flake — not claimed green without it). Receipts updated in
evidence/validation-receipts.md.

## item
ZCode carrier staged comparison (replaces the send-gate direction in the
earlier result, which stays as history): compare a minimal Host/Skill-layer
carrier — orchestrator-procedure behavior that includes the recovery text in
the next host prompt when the controlling Agent observes a compaction —
against a UserPromptSubmit hook (in-runtime, covers all prompts, needs
hooks.enabled + user-global merge + own detection sentinel). Explicitly do
NOT implement a generic per-send db.sqlite query gate or a new cursor
ledger — that pollutes the transport-only boundary. Keep every unverified
item marked unverified; produce staged evidence only.
status: done
dispatched: self; comparison lands in
kaola-workflow/bundle-75/evidence/zcode-compact-mechanism.md (revised
section 5/6); live verification still gated on #79 merging to main.
result: done — zcode-compact-mechanism.md section 5 rewritten as a staged
comparison: Candidate H (Host/Skill-layer orchestrator procedure — carrier
rides the next Runner-composed prompt when the Agent observes compaction;
zero ZCode mutation, zero transport change, keeps transport-only boundary)
recommended; Candidate U (UserPromptSubmit hook — wider coverage incl.
interactive prompts, costs user-global hooks.enabled write + per-prompt
process + sentinel state) kept as documented fallback. The earlier
send-gate/db-cursor-machine direction is explicitly withdrawn as shipped
machinery (boundary violation); the part-table cursor survives only as an
optional corroboration check in the live plan. All unverified items marked
unverified; live run still gated on #79 merging to main.

## item
ZCode live compact-recovery experiment + minimal carrier ship (new
authorization sync: #79 adapter is on main at b40813f). Bounded isolated
real compact in a scratch Git repo via the merged ACP adapter: trigger a
real /compact, prove the next-prompt Host/Skill-layer carrier makes the
model re-read the installed Skill, distinguish manual vs auto honestly,
and ship the verified minimal mechanism as an orchestrator reference —
no send DB gate, no cursor ledger, no UserPromptSubmit user-global change,
no credentials, no other session. Rebase the Codex candidate onto the new
main, re-render, re-test, re-validate, freeze a new SHA.
status: done
dispatched: self; fixture /tmp/kpr-i75-zcode/repo (scratch, throwaway);
evidence lands in kaola-workflow/bundle-75/evidence/zcode-compact-live/;
code lands in templates/orchestrator/references/zcode-compact-recovery.md
+ host-startup.md.tmpl pointer + docs/zcode-host.md + CHANGELOG.md +
tests/contract/test-issue-75-codex-compact-hook.py on workflow/bundle-75
(rebased onto b40813f).
result: done — real manual /compact verified through session/prompt text
(db part-table rows trigger:"manual", auto:false, standalone_turn,
operationId cmp_d814b072, committed synchronously); post-compact carrier
prompt drove a real read of the planted Skill and the model quoted
KPR-SKILL-RELOAD-7931 — the Host/Skill-layer carrier is verified and
shipped as references/zcode-compact-recovery.md (KPR-ZCODE-RECOVERY-V1 +
KPR-SKILL-RELOAD-V1, once-per-episode, diagnostic-only part cursor,
UserPromptSubmit kept as documented fallback). Compaction is silent in the
ACP stream (observe/capture/context_usage all empty) — detection premise
revised honestly. Auto-compact and non-Runner prompts stay untested and
marked so. Exact stop: stopped:true, exit 0, residual_pids=[]. i75 suite
15/15; render --check PASS.
Frozen: 7c1b5c6 on latest main 88042cd (post-#79/#80/#83; three CHANGELOG/
list conflicts resolved keeping every entry). Full validate.sh rerun on the
final base: PASS, no env mitigation — unqualified green (#80 fixed the #49
teardown race in fixtures).

- item: ZCode native UserPromptSubmit hook — isolated live verification
  (outer-review round 2). In a scratch repo with a project-scoped
  plugins.dirs fixture (zero user-global writes), prove the native hook
  fires on installed ZCode 3.12.3/CLI 0.16.5, detects compaction from
  existing part records read-only (no new ledger, no send gate, no
  heartbeat), and injects additionalContext that reaches the model's next
  reasoning — for typed /compact AND programmatic session/compact RPC;
  attempt runtime auto compaction within bounded cost and state the
  result honestly.
  status: done
  dispatched: self; fixture /tmp/kpr-i75-native/{repo,plugin,hook.*,state};
  direct driver direct-drive.py imports the merged adapter's backend+auth
  helpers; evidence lands in
  kaola-workflow/bundle-75/evidence/zcode-compact-live/{FINDINGS-native-hook.md,
  hook-invocations.jsonl,rpc-compact-events.jsonl}; mechanism verdicts in
  evidence/zcode-compact-mechanism.md §5-6.
  result: done — UserPromptSubmit plugin hook live-verified end-to-end:
  fires on every normal prompt (7 invocations / 3 sessions), detects
  compaction via read-only part-cursor once per episode, injected
  additionalContext drove a real read of the planted Skill and marker
  quote KPR-SKILL-RELOAD-8842 after BOTH typed /compact (sess_194d7421,
  trigger:"manual", standalone_turn) AND programmatic session/compact RPC
  (sess_25e3d20d, compact_started, operationId compact_c3390f77,
  identical part records) — mid-run programmatic coverage proven.
  /compact itself bypasses the hook; user cli/config.json kept hooks:{}.
  Runtime auto compaction UNTRIGGERED at bounded cost: GLM-5.3 climbed
  to 494,040 input tokens with zero compaction parts; live
  contextWindow:1,000,000 => threshold ~966k+ (~8M provider tokens);
  GLM-5.3-Flash (also 1M) absorbed 288,926 tokens. trigger:"auto"
  coverage is inferred (same schema, trigger-agnostic read), not
  observed — stated honestly, not claimed. Proposed minimal boundary
  (project plugins.dirs + plugin hook; session/compact not adapter-
  reachable today) recorded for outer review, not shipped. Exact stop:
  stopped:true x2, residual_pids:[], scratch repo clean, no credentials
  or other sessions touched.
  Frozen: 8b8abbc on 88042cd (docs/zcode-host.md round-2 verdicts; no
  shipped mechanism change — Candidate H stays shipped, Candidate U
  live-verified and proposed for boundary decision). Gate on the frozen
  SHA: render --check PASS, i75 suite 15/15, validate.sh PASS
  (residual_pids=[], no env mitigation).

- item: ZCode durable-prefix carrier — answer the outer audit's two
  bounded questions (round 3). Verify whether SessionStart/AGENTS
  additionalContext is in the durable compact-preserved prefix, and
  attempt real auto compaction only if a plausible safe path exists;
  otherwise report exact BLOCKED facts.
  status: done
  dispatched: self; fixture /tmp/kpr-i75-native/repo + planted AGENTS.md
  (KPR-AGENTS-DURABLE-5520 + standing instruction KPR-PREFIX-CARRIER-V1);
  session kpr-i75-agents / sess_4f59f76d; evidence lands in
  kaola-workflow/bundle-75/evidence/zcode-compact-live/
  FINDINGS-durable-prefix.md; mechanism verdicts in
  evidence/zcode-compact-mechanism.md §5-6.
  result: done — (a) AGENTS additionalContext IS in the durable
  compact-preserved prefix, verified live: post-compact with no carrier
  in the prompt the model still quoted the AGENTS-only marker
  KPR-AGENTS-DURABLE-5520 (AGENTS.md -> contextSourceSnapshot.
  userInstructions -> per-request context prefix, outside rewritten
  history; hook additionalContext lands in history instead and is not
  durable). The standing instruction then drove a real read of the
  planted SKILL.md and the model quoted KPR-SKILL-RELOAD-8842 reasoning
  "context was compacted" — a planted AGENTS block is a trigger-agnostic
  carrier covering ANY compaction incl. the first post-compact inference
  (the mid-turn/same-turn case), with zero hooks, detection, sends, or
  ledgers. (b) No plausible safe path to trigger:"auto": both catalog
  models are 1M-window (GLM-5.3 live contextWindow:1,000,000), threshold
  pressure needs ~8M provider tokens, session/setModel resolves through
  the provider registry (builtin table — no caller window),
  provider/updateAccountConfig has no per-model contextWindow,
  config.compact/contextWindow/midConversationSystem are not
  config-file/session-create keys, reactive compact needs provider
  overflow at the same 1M wall — BLOCKED as live observation, stated
  exactly; auto coverage is by construction (prefix never in rewritten
  history). Real compaction this session: cmp_918b57d0, trigger:"manual",
  standalone_turn, summarySource:"model". Exact stop: stopped:true,
  residual_pids:[], scratch repo clean, no credentials/user config
  touched. Proposed minimal boundary (merge-managed AGENTS.md block)
  recorded for outer review, not shipped.
  Frozen: e2a8316 on 88042cd (docs/zcode-host.md round-3 durable-prefix
  verdict). Gate on the frozen SHA: render --check PASS, i75 suite
  15/15, validate.sh PASS exit 0 (residual_pids=[], no env mitigation).

- item: ZCode real auto-compact leg — one bounded isolated validation:
  custom MOCK provider (declared contextWindow:8192, scratch HOME only,
  zero user-global writes, fake key) → real trigger:"auto" → post-compact
  wire request still carries the AGENTS durable prefix.
  status: done
  dispatched: self; fixture /tmp/kpr-i75-mock/{home,repo,provider_config,
  mock_server.py,drive.py}; installed ZCode 3.12.3 unpatched; adapter's own
  ZCODE_PERSONAL_PROVIDER_CONFIG_FILE env path used for isolation.
  result: done — real trigger:"auto" compactions observed live for the
  first time: 7 completed operationIds on sess_c46bd933 (auto:true,
  phase:"pre_request", compactReason:"context_limit", status:"completed",
  23 compaction part rows), fired whenever accumulated tokens crossed the
  declared 8192 window (~7.5–7.9k observed request sizes). Wire evidence:
  every conversation inference after each completed auto-compaction
  carried the # agentsMd section + standing instruction text
  (has_prefix_marker on all 16 conversation requests; only false = off-band
  title-generation call); post-compact requests carry the runtime-written
  continuation header while the prefix precedes it unchanged. Verdict:
  Candidate A's prefix survival is now observed end-to-end for
  trigger:"auto", not inferred — the audit's "automatic same-turn" bar is
  met at the wire level. Stated limits: mock cannot prove real-model
  behavior (that leg stays with round-3 GLM manual-compact Skill-read);
  observed phase pre_request; declared-window is a test-isolation
  technique, not production config. Isolation: scratch HOME only;
  ~/.zcode untouched (hooks:{} unchanged); mock on 127.0.0.1 only; no
  credentials copied/decrypted/logged; installed app unpatched; exact
  stop, residual_pids:[].
  Evidence: zcode-compact-live/{FINDINGS-auto-compact.md,
  auto-compact-parts.jsonl, mock-requests.jsonl, provider_config.json,
  AGENTS.md.fixture} — sanitized (fake key only).
  Frozen: 6ac2d49 on 88042cd (docs/zcode-host.md round-4 auto-compact
  verdict). Gate on the frozen SHA: render --check PASS, i75 suite
  15/15, validate.sh PASS exit 0 (residual_pids=[], no env mitigation).

- item: Minimal candidate prep per outer review of 6ac2d49 (comment
  5735423572): document the owner-authorized AGENTS.md standing
  instruction as the only live-verified durable carrier; reusable
  marker-free block; correct auto-verification wording; no auto-write,
  no global hook, no polling/gate.
  status: done
  dispatched: self; templates only — zcode-compact-recovery.md
  restructured (durable vs per-send carriers), host-startup.md.tmpl
  compact note updated, new contract test
  test-issue-75-zcode-compact-recovery.py (13 tests), validate.sh wired.
  result: done — reference now states the only durable carrier verified
  by real experiment is the owner-authorized pre-session AGENTS.md
  standing instruction; per-send carrier documented as the known-
  compaction fallback that cannot alone cover automatic same-turn.
  Reusable block ships marker-free (only <installed SKILL.md path>
  fill-in; serves kaola-project-runner or kaola-delegator; reload proof
  stays inside the Skill payload). Recovery semantics: re-read Skill in
  use → effective authorization/heartbeat/in-flight records → never
  re-dispatch. Evidence wording corrected: real runtime trigger:"auto"
  + mock prefix-on-wire verified; real-GLM auto behavior not verified;
  manual GLM verified. Boundaries pinned by 13 contract tests: never
  writes consuming AGENTS.md, no global hook, no polling, transport-only,
  never a transport gate/cursor ledger. Activation requires explicit
  project-owner consent — user choice pending; NOT adopted anywhere.
  Frozen: b3aa648 on 88042cd. Gate: render --check PASS (budgets OK),
  i75 suites 15/15 + 13/13, validate.sh PASS exit 0 (residual_pids=[],
  no env mitigation).

- item: Role-scope the durable AGENTS block per outer review of
  b3aa648: every workspace Agent reads AGENTS.md, so an unscoped block
  could make an ordinary Worker self-promote into a runner (violates
  one-Runner-per-project). Scope to the designated Host; prove by role
  contrast; scope the per-send carrier likewise; freeze new SHA.
  status: done
  dispatched: self; reference + fixture + contract test only; live
  role-contrast leg on scratch repo /tmp/kpr-i75-native/repo (real GLM,
  yolo, session kpr-i75-worker).
  result: done — reusable block now opens "Compact recovery (designated
  Project Runner Host only)": applies only to the designated ZCode
  Project Runner Host or an outer host genuinely running
  kaola-delegator; Ordinary Workers and single-issue Workflow Agents
  are told to ignore it entirely — it never makes a worker into a
  runner. Per-send carrier targets the compacted Host session only
  ("the designated ZCode Project Runner Host", never an ordinary
  Worker). Live role contrast on real GLM (kpr-i75-worker): worker-role
  prompt completed its task with zero reads and answered the block does
  not apply to it (0 tool calls); host-role prompt re-read the Skill
  and quoted KPR-SKILL-RELOAD-8842 with no re-dispatch. Contract tests
  pin the scoping (15 tests incl. role-contrast + per-send scoping).
  No other mechanism extended; no consuming AGENTS.md touched.
  Frozen: 835cbc6 on 88042cd. Gate: render --check PASS (budgets OK),
  i75 suites 15/15 + 15/15, validate.sh PASS exit 0 (residual_pids=[],
  no env mitigation). Exact stop on kpr-i75-worker; scratch repo clean.

- item: Codex hook outer-release audit, 2xP1 (round on 835cbc6; NO
  finalize/sink, NO rebase — main moving with #87): (a) the installer
  writes a global CODEX_HOME/hooks.json SessionStart(compact) entry that
  injects Runner/Delegator recovery into ANY Codex session incl. ordinary
  Workers — design a minimal machine-verifiable Host-only filter: install
  binds the exact designated Host session_id + canonical project root
  (official hook stdin carries session_id + cwd); hook emits ONLY on
  match, nothing for Worker/other repo; no periodic checks/second state;
  preserve foreign hooks + Workflow coexistence; no global user install
  during tests. (b) load_hooks accepts JSON-null `hooks` /
  `hooks.SessionStart`, writes payload, then TypeErrors — validate shape
  BEFORE any write, refuse atomically; add null regression. Also: prove
  or remove the unverified `.zcode/AGENTS.md` alternative claim.
  Failure-first tests: matching Host vs ordinary Worker vs other repo,
  malformed null config, source compact only, actual isolated Codex
  compact if possible. Freeze new SHA; render/focused/full validate +
  diff check; report then STOP.
  status: done
  dispatched: self; code lands in scripts/kaola-codex-compact-hook.py +
  tests/contract/test-issue-75-codex-compact-hook.py + docs/codex-host.md
  + CHANGELOG.md + templates/orchestrator/references/zcode-compact-recovery.md
  (re-render) on workflow/bundle-75; live evidence in
  kaola-workflow/bundle-75/evidence/codex-compact-live/.
  result: done — three outer-review P1s resolved and re-verified. (a)
  Host-only filter: emit prints the payload only for SessionStart(compact)
  whose stdin session_id + realpath cwd match the binding. (b) Multi-project
  P1 (comment 5736151615): config moved to per-project
  <repo>/.codex/hooks.json with project-private assets under
  .codex/kaola-project-runner/hooks/ — A/B coexist, uninstall strictly local,
  nothing writes CODEX_HOME/~/.codex. (c) First-session bootstrap P1:
  two-phase prepare (inert session_id:null binding BEFORE Host start — hooks
  load at session start) + bind (writes ONLY binding.json; hooks.json
  byte-identical); install kept as one-shot prepare+bind. Null/malformed
  config refused before any write on every action. CODEX_SESSION_ID +
  CODEX_THREAD_ID inside the Codex host shell verified == rollout/hook-stdin
  session_id (live, masked; 54-repo5-env-compare.json). `.zcode/AGENTS.md`
  claim disproven by binary inspection and corrected in the template
  (project AGENTS.md upward-walk + user-global ~/.zcode/AGENTS.md only).
  Live proof on codex 0.153.4 (repo5): inert compact → KW-only; bind;
  compact same session → KW+KPR markers; Worker session → KW only.
  Contract: 27/27 codex + 15/15 zcode. Gates: render --check PASS,
  validate.sh PASS exit 0 (residual_pids=[], no env mitigation), diff
  --check clean. Evidence: evidence/codex-compact-live/ rounds 2–3,
  evidence/validation-receipts.md. Frozen: 930df9a on 835cbc6. STOP — no
  finalize/sink/rebase pending outer ACCEPT.
