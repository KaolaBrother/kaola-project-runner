# ZCode 3.12.3 — minimal post-compact recovery trigger (static verification)

Date: 2026-09-19. Subject: `/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs`
(ZCode 0.16.5, bundle dated 2026-09-16). Method: read-only static analysis of the
installed bundle plus read-only schema inspection of `~/.zcode/cli/db/db.sqlite`.
No process was launched, no credential store or message body was read, no config
was written.

## 1. Hook event surface (complete, binary-verified)

The event enum appears identically in five places (invocation schema, review
schema, admission schema, digest schema, runtime registry):

```
SessionStart, UserPromptSubmit, PreToolUse, PermissionRequest,
PostToolUse, PostToolUseFailure, Stop
```

**No compact event exists** — there is no `PreCompact`, `PostCompact`,
`SessionEnd`, `Notification`, or `SubagentStop` anywhere in the enum.

`runSessionStartHooks` has exactly two call sites — `"startup"` and `"resume"`
— gated once per session by `sessionStartHookRan`. **SessionStart(compact)
cannot fire in 0.16.5** (re-confirmed at the dispatch layer).

## 2. What CAN inject model-visible context

`hookSpecificOutput.additionalContext` (and top-level `additionalContext` /
`additional_context`) is accepted for `SessionStart`, `UserPromptSubmit`,
`PostToolUse`, `PostToolUseFailure`, and `Stop`, and is pushed into
`additionalContexts`, then made model-visible via
`injectHookAdditionalContextIntoMessageHistory(<event>, contexts)` — the same
channel Codex's `additionalContext` uses.

- `UserPromptSubmit` runs on every submitted prompt with input
  `{agentName,cwd,hookEventName,mode,prompt,sessionId,timestamp,traceId,turnId}`;
  its `additionalContexts` are injected into message history **before the
  model sees that prompt**.
- `Stop` runs at turn end with `responseText`/`stopHookActive`; a
  `continue:true`/`decision:"block"` result forces another turn and injects
  `additionalContexts` — heavier (extra turn), kept as fallback only.
- An internal "Session mailbox" already delivers pending inputs as
  `additionalContext` on `UserPromptSubmit`/`PostToolUse`/`Stop`
  (`clientVisible:false`, `sourceKind:"internal"`) — the existing wake/steer
  channel, not a hook the user installs.

## 3. Hook config schema (verified)

```
cli/config.json  →  hooks: { enabled?, timeoutMs?, maxOutputBytes?,
                    events: { <Event>: [ { matcher?, hooks: [
                      {type:"command"|"process", command, args?,
                       timeoutMs?, statusMessage?, enabled?} ] } ] } }
```

Enable is three-level: source `hooks.enabled` × declaration `enabled` ×
runtime root. Current user config has `hooks: {}` — empty object, `enabled`
unset, zero events. Any hook-based mechanism requires writing real
user-global config (or a plugin `hooks/hooks.json`); nothing exists to
merge into today.

## 4. Deterministic compaction detection (verified)

Compaction is persisted in the session store, not just the UI:

- `part` table (`db.sqlite`): `session_id`, `time_created`, `data` (JSON).
  Compaction lands as `type:"compaction"` parts and
  `timelineType:"context_compaction"` timeline parts (`operationId`,
  `boundaryId`, `summaryMessageId`, `tail_start_id`, `trigger`,
  `compactReason`, `phase`) via `persistAssistantTimelinePartForSession`.
- Both **manual `/compact`** (`executeManualCompact`) and **automatic
  context-pressure compaction** (`compactionTrigger`,
  `compactionOuterAttempt`) write the same records — a cursor on the table
  covers both triggers.
- `rollout/model-io-sess_<sessionId>.jsonl` also logs compaction model calls
  (`operation:"context_compaction"`) but is gated by `recordModelIO`
  (opt-in) — usable as a secondary source only.

Read-only cursor query (no message bodies, marker only):

```sql
SELECT MAX(time_created) FROM part
WHERE session_id = :sid
  AND (data LIKE '%"context_compaction"%' OR data LIKE '%"type":"compaction"%');
```

## 5. Candidate mechanisms compared (revised — staged, unverified)

Boundary ruling from outer review of the first draft: a **per-send
`db.sqlite` query plus injection policy implemented in the Runner send path
is rejected** — it would run inside the transport layer for every prompt,
pollute the transport-only boundary, and amount to a new cursor ledger.
Sections 1–4 (facts) stand; the earlier "send-path carrier" primary
recommendation is withdrawn as shipped machinery. What follows compares the
two remaining honest candidates; **H's carrier leg is now live-verified**
(see §6).

### Candidate H — Host/Skill-layer carrier (orchestrator procedure, no ZCode machinery)

The recovery text is an Agent-side behavior, not a mechanism: when the
controlling Agent knows a compaction happened in its bound ZCode host, the
next wake/dispatch prompt it composes carries the KPR carrier inline.

- Detection, revised by live evidence: an Agent-requested `/compact` is
  self-evident (the primary case). Everything else is **silent in the ACP
  stream** — `observe`, `capture --tools`, `capture --full` expose no
  compaction field and `context_usage` stays null (verified live). The
  read-only `part`-table cursor is the corroborating diagnostic for
  compaction the Agent did not request; its rows commit synchronously
  (verified live). It stays a diagnostic, never a per-send check.
- Zero ZCode mutation, zero transport change, zero new state. The nine
  worker Skills stay transport-only; the procedure lives in the
  orchestrator Skill/host doc where prompt composition already lives.
- Coverage: every Runner-authored prompt (the only prompts a Runner host
  should ever get). Human-typed pane input is out of contract anyway.
- Live-verified: the carrier itself. Post-compact, one carrier prompt made
  the model execute a real `read` of the installed Skill and quote the
  planted reload marker (`KPR-SKILL-RELOAD-7931`) — see
  `zcode-compact-live/FINDINGS.md`.
- Honest residuals: an unobserved auto-compaction means a missed carrier
  (degraded, not corrupt — the host proceeds with compacted context, the
  status quo); auto-compaction itself was not exercised live.

### Candidate U — `UserPromptSubmit` hook (in-runtime) — **live-verified (round 2)**

One entry under `hooks.events.UserPromptSubmit` or — as actually proven —
a plugin `hooks/hooks.json` reached through project-scoped
`plugins.dirs`. On each prompt the command checks the `part` cursor
against its own sentinel and prints
`{"hookSpecificOutput":{"additionalContext":"<carrier>","hookEventName":"UserPromptSubmit"}}`
only when a compaction is newer than the sentinel.

- Coverage: every prompt including interactive ones — strictly wider than H.
- Costs: the plugin channel needs **no user-global write at all** —
  `plugins.dirs` is project config, plugin hooks dispatch
  `sourceKind:"plugin"` and bypass workspace trust admission; user
  `cli/config.json` stayed `hooks:{}` throughout (verified). Residual
  costs: one spawned process per prompt; sentinel file = hook-owned state
  under `$ZCODE_PLUGIN_DATA`.
- Live-verified (round 2, `FINDINGS-native-hook.md`): hook fires on every
  normal prompt; detects compaction from existing `part` rows; injected
  `additionalContext` reaches the model's next reasoning (real `read` +
  quoted marker); once-per-episode cursor holds; `/compact` itself
  bypasses the hook (no spurious injection); identical outcome for both
  typed `/compact` and the programmatic `session/compact` RPC.

### Candidate A — durable AGENTS-prefix carrier — **live-verified (rounds 3–4)**

A standing-instruction block in the workspace `AGENTS.md`: the runtime
loads it once per session into `contextSourceSnapshot.userInstructions`,
which feeds the per-request context prefix — **orthogonal to message
history, so it survives compaction by construction**. The block carries a
marker plus a conditional rule ("if the Skill's full text is no longer in
context, read it before runner work").

- Coverage: **every model request**, including the first inference after
  any compaction — manual, `session/compact`, or runtime auto; the prefix
  is never inside the rewritten history, so coverage does not depend on
  detecting the trigger at all. This is the only candidate that covers
  the mid-turn/same-turn inference the audit requires.
- Costs: a merge-managed block in a project file (`AGENTS.md` /
  `.zcode/AGENTS.md`), present before session start; model-behavioral
  reliability like every prompt-layer carrier; mid-session AGENTS edits
  are not guaranteed to refresh the snapshot.
- Live-verified (round 3, `FINDINGS-durable-prefix.md`): post-compact
  marker still quoted (prefix durable); the standing instruction drove a
  real `read` of the planted Skill and the model quoted
  `KPR-SKILL-RELOAD-8842`, reasoning "context was compacted". Zero hooks,
  zero detection, zero sends.
- Wire-verified for `trigger:"auto"` (round 4,
  `FINDINGS-auto-compact.md`): real auto compactions
  (`compactReason:"context_limit"`, `phase:"pre_request"`,
  `status:"completed"`) in the installed runtime on a declared-window MOCK
  provider; the request immediately following each compaction still
  carried the `# agentsMd` section and the standing instruction — prefix
  survival observed on the wire, not inferred.

### Staged verdict — resolved by live evidence

**A is now the live-verified strongest option**: trigger-agnostic by
construction and now observed end-to-end for `trigger:"auto"` (round 4 —
prefix present in the first inference after real auto compactions), zero
machinery, and the only candidate whose carrier is guaranteed present in
the first post-compact inference. Its adoption is a boundary decision for
outer review — a standing block in the consuming project's AGENTS.md —
not shipped in this candidate.

**H is verified and shipped** as `references/zcode-compact-recovery.md`
(pointer from `host-startup.md`): no new machinery anywhere, the
transport-only boundary holds, and the carrier demonstrably makes the model
re-read the installed Skill after a real `/compact`. H remains the
fallback where no AGENTS block can be planted.

**U is live-verified** (round 2): same proven carrier outcome, wider
coverage than H (runtime-injected on every prompt), plugin channel needs
no user-global write. Weaker than A: needs a process per prompt and
detection state; its advantage is not requiring a workspace file at
session start.

**Rejected, unchanged:** `SessionStart` matchers cannot fire post-compact;
`Stop` hook forces an extra turn (heavier); workspace `.zcode/hooks.json`
is admission-gated, not runnable; `PostToolUse` needs tool activity an
idle host may lack; a transport-level per-send db query is a boundary
violation.

## 6. Live verification results (ran after #79 landed on main)

Full record: `zcode-compact-live/FINDINGS.md` + `events.jsonl` +
`db-compaction-parts.json`. One deviation from the plan: the adapter's env
allowlist does not forward `ZCODE_STORAGE_DIR`, so the session lived in the
runtime's real `~/.zcode` store — its own session data, inspected strictly
read-only; nothing user-global was written.

1. `/compact` as prompt text → real manual compaction (`trigger:"manual"`,
   `auto:false`, `phase:"standalone_turn"`), `part` rows committed
   synchronously.
2. Compaction is **not** visible in the ACP stream — H's detection premise
   revised to "Agent-requested is self-evident; `part` cursor is the
   diagnostic for the rest".
3. Carrier prompt → real `read` of the installed Skill → reload marker
   `KPR-SKILL-RELOAD-7931` quoted. Mechanism proven.
4. Counterfactual: the planted fact (`ZEBRA-991`) survived manual compact
   via the summary — the carrier exists for re-instruction, not fact
   recovery.
5. Exact stop: `stopped:true`, `agent_exit_code:0`, `residual_pids:[]`.

Honestly untested: auto-compaction live; carrier on non-Runner prompts;
multi-compaction repetition beyond one resend.

### Round 2 — native `UserPromptSubmit` plugin hook (`FINDINGS-native-hook.md`)

Isolated plugin fixture (project `plugins.dirs`, zero user-global writes),
installed ZCode 3.12.3 / CLI 0.16.5:

1. Hook fires on every normal prompt (7 invocations, 3 sessions) —
   `UserPromptSubmit` is a working injection channel on the installed build.
2. Detection from existing `part` rows, read-only, once per episode —
   no new ledger; `/compact` itself bypasses the hook.
3. Injected `additionalContext` reaches the model's next reasoning: real
   `read` of the planted Skill + quoted marker `KPR-SKILL-RELOAD-8842` —
   proven after both typed `/compact` and the programmatic
   `session/compact` RPC (`compact_started`, `operationId`, summarization
   call, identical `trigger:"manual"` part records).
4. `session/compact` is a mid-run programmatic trigger — compaction not
   authored as prompt text. It is **not** reachable through the adapter's
   fixed method dispatch today.
5. Auto compaction (`trigger:"auto"`) **not triggered at bounded cost**:
   GLM-5.3 climbed to 494,040 input tokens with zero compaction parts;
   live `session.updated` reports `contextWindow: 1,000,000` (threshold
   ≈966k+, ~8M provider tokens to cross). GLM-5.3-Flash (also 1M per
   vendor spec) absorbed 288,926 tokens, zero compaction. Coverage of
   `trigger:"auto"` is inferred (identical schema, trigger-agnostic
   read), not observed.
6. Exact stop on both sessions; `residual_pids:[]`; user config and
   credentials untouched.

### Round 3 — durable AGENTS-prefix carrier (`FINDINGS-durable-prefix.md`)

Answers to the outer audit's two bounded questions, session
`sess_4f59f76d` (kpr-i75-agents, GLM-5.3, yolo, scratch repo):

1. **AGENTS `additionalContext` IS in the durable compact-preserved
   prefix — verified live.** `AGENTS.md` loads into
   `contextSourceSnapshot.userInstructions` (once per session) feeding
   the per-request context prefix; hook `additionalContext` instead lands
   in message history via
   `injectHookAdditionalContextIntoMessageHistory` and is rewritten by
   compaction. Post-compact, with no carrier in the prompt, the model
   still quoted the AGENTS-only marker `KPR-AGENTS-DURABLE-5520`.
2. **Durable-prefix carrier works end-to-end.** Standing instruction
   `KPR-PREFIX-CARRIER-V1` in AGENTS.md → post-compact runner prompt →
   real `read` of `.kpr/skills/kaola-project-runner/SKILL.md` → quoted
   `KPR-SKILL-RELOAD-8842`, reasoning "context was compacted". Zero
   hooks, detection, sends, or ledgers; coverage is trigger-agnostic by
   construction (the prefix is in every request, including the first
   inference after any compaction — the mid-turn case included).
3. **No plausible safe path to `trigger:"auto"` — BLOCKED as a live
   observation at that time.** Both catalog models are 1M-window (GLM-5.3
   measured `contextWindow:1,000,000`); threshold pressure needs ~8M
   provider tokens; `session/setModel` resolves through the provider
   registry (builtin table — caller cannot declare a smaller window);
   `provider/updateAccountConfig` has no per-model `contextWindow`;
   `config.compact`/`contextWindow`/`midConversationSystem` are not
   config-file or `session/create` keys; reactive compact needs provider
   overflow at the same 1M wall. *Round 4 superseded this: a safe path
   existed via an isolated personal-provider model-rule override — see
   below.*
4. Exact stop: `stopped:true`, `residual_pids:[]`, scratch repo clean.

### Round 4 — real `trigger:"auto"` + wire-level prefix survival (`FINDINGS-auto-compact.md`)

Outer review authorized one bounded leg: official ZCode configuration docs
say custom-provider context windows are editable. An isolated
personal-provider declaration (`mock-local/mock-small`,
`contextWindow:8192`, MOCK OpenAI-compatible endpoint, scratch `HOME`
only — zero user-global writes, fake key) let the **installed** runtime
exercise its real compaction machinery:

1. **Real `trigger:"auto"` compactions observed** — 7 completed
   `operationId`s in one session (`auto:true`, `phase:"pre_request"`,
   `compactReason:"context_limit"`, `status:"completed"`), fired whenever
   accumulated tokens crossed the declared window (~7.5–7.9k of 8192).
   First live observation of auto-compaction records in this
   investigation — previously only inferred.
2. **The AGENTS durable prefix survives on the wire**: every
   conversation inference after each completed auto-compaction carried
   the `# agentsMd` context section and the standing instruction text
   (`has_prefix_marker` on all 16 conversation requests; the only `false`
   was an off-band title-generation call). The first inference after a
   real auto-compaction provably receives the standing carrier.
3. **Real history rewrite observed**: post-compact requests carried the
   runtime-written continuation header — while the `# agentsMd` prefix
   preceded it unchanged.
4. **Stated limits**: the mock cannot prove real-model *behavior* (GLM
   acting on the instruction post-auto-compact) — that leg stays with the
   round-3 manual-compact real-model proof; observed phase is
   `pre_request`; the declared-window mechanism is a test-isolation
   technique, not a production configuration.
5. Exact stop; `residual_pids:[]`; personal `~/.zcode` untouched.
