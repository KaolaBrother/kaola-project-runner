# ZCode durable-prefix compaction carrier — live findings (round 3)

Scope: answer the outer audit's two bounded questions on installed ZCode 3.12.3 /
CLI 0.16.5 — (a) is SessionStart/AGENTS `additionalContext` in the durable
compact-preserved prefix; (b) is there a plausible safe path to real
`trigger:"auto"` compaction. Isolated scratch repo, no user-global writes, no
credentials touched.

## Static facts (installed bundle)

- Hook `additionalContext` (SessionStart / UserPromptSubmit / Stop) is injected
  via `injectHookAdditionalContextIntoMessageHistory` — it lands in **message
  history** and is rewritten by compaction. Not durable. (Confirms the audit.)
- `AGENTS.md` loads through `NodeContextSourceAdapter` (workspace `AGENTS.md`,
  `.zcode/AGENTS.md`, `.agents/AGENTS.md`, user `~/.zcode/AGENTS.md`; 100 KB cap)
  into `contextSourceSnapshot.userInstructions`, resolved **once per session**
  (`contextInitialized` gate). The snapshot feeds `contextBuilder` — a
  per-request context prefix (`# agentsMd` section, `cacheHint:"dynamic"`),
  orthogonal to `messageHistory`. `isContextPrefixMessage` exists to exclude
  prefix content from compaction accounting.
- Compact boundary records carry `preservedSegment`, `hookResultMessageIds`,
  `attachmentMessageIds`, `customInstructions` — observed boundary:
  `customInstructions:false`, `summarySource:"model"`.
- No caller-settable `contextWindow`: `session/setModel` resolves through the
  provider registry (builtin model table); `provider/updateAccountConfig`
  provider entries accept `builtinModelIds`/`personalModelIds`/`access`/`api`
  only; `config.compact`, `contextWindow`, `midConversationSystem` are not
  config-file or `session/create`/`runtimeConfig` keys.

## Live results — session `sess_4f59f76d` (kpr-i75-agents, GLM-5.3, yolo)

Planted: `AGENTS.md` with marker `KPR-AGENTS-DURABLE-5520` + standing
instruction `KPR-PREFIX-CARRIER-V1` ("if the Skill's full text is no longer in
context — e.g. after compaction — read `.kpr/skills/kaola-project-runner/
SKILL.md` before runner work").

| Step | Result |
|---|---|
| P0 pre-compact marker probe | `final_text:"KPR-AGENTS-DURABLE-5520"` — AGENTS prefix live |
| P1 `/compact` | real compaction: `cmp_918b57d0`, `trigger:"manual"`, `standalone_turn`, `summarySource:"model"`, pre 6630 → post 18585 |
| P2 post-compact marker probe (no carrier in prompt) | **`final_text:"KPR-AGENTS-DURABLE-5520"` — the AGENTS prefix survived compaction** |
| P3 post-compact runner prompt (no carrier in prompt) | `tool_calls:{read:1}` on the planted SKILL.md; `final_text` quotes **`KPR-SKILL-RELOAD-8842`** and explicitly reasons "context was compacted, so the Skill's full text had to be reloaded" |
| P4 second runner prompt | marker quoted; model re-read conservatively (correct, not minimal — the conditional wording can be tuned for frugality) |

## Verdicts

1. **AGENTS `additionalContext` IS in the durable compact-preserved prefix** —
   verified live (P2). SessionStart/hook `additionalContext` is NOT (history).
2. **The durable-prefix carrier achieves automatic, trigger-agnostic
   recovery** — the standing instruction rides every model request, including
   the first inference after ANY compaction (manual, `session/compact`, or
   runtime auto — the prefix is never inside the rewritten history). No
   detection, hook, db cursor, send-gate, or ledger is needed. This is the
   "reliable reload before the next critical inference" property Issue #75
   requires, including the mid-turn case the audit called out: whatever step
   follows a compaction already carries the prefix.
3. **Skill body is NOT in the prefix** — confirmed (P3 required a real
   `read`); the carrier must reference the file path, which it does.
4. **`trigger:"auto"` remains unreachable at bounded cost** — BLOCKED as a
   live observation: both catalog models are 1M-window (GLM-5.3
   `contextWindow:1,000,000` measured live), threshold pressure needs ~8M
   provider tokens, and no config surface can declare a smaller window
   (registry-owned properties). The mechanism does not depend on the trigger
   identity, so auto coverage is by construction rather than observation —
   stated precisely, not inflated.

## Costs and limits (honest)

- The workspace must carry the standing-instruction block in an AGENTS.md the
  runtime loads **before session start** (snapshot resolved once at init).
  For Runner use that means a merge-managed block in the consuming project's
  `AGENTS.md` (or `.zcode/AGENTS.md`) — a project file, not user-global.
- Reliability is model-behavioral, like every prompt-layer carrier: the
  conditional is a standing instruction, not a mechanical gate. Observed
  behavior was correct including its own compaction reasoning.
- `contextSourceSnapshot` is fixed at session init — mid-session AGENTS.md
  edits are not guaranteed to refresh (`envInfo` has a refresh path;
  `userInstructions` refresh unverified).
- `trigger:"auto"` records were not produced; phase variants other than
  `standalone_turn` unobserved.

## Proposed minimal boundary (for outer review — not shipped)

Candidate A — durable AGENTS-prefix carrier: a small standing-instruction
block (marker + conditional reload rule) in the consuming workspace's
AGENTS.md, managed as a mergeable block. Stronger than H (no detection or
send needed; covers non-Runner prompts and the same-turn inference) and U
(no per-prompt process, no plugin, no hooks). H and U remain verified
fallbacks where no AGENTS.md block can be planted.

## Stop evidence

`kpr-i75-agents` stopped: `stopped:true`, `agent_exit_code:0`,
`residual_pids:[]`, scratch repo `dirty:false`.

## Round-3b — role-scoping contrast (scoped block, real GLM)

The reusable block was role-scoped per outer review (one Runner per
project; every workspace Agent reads AGENTS.md). Live check on
`sess_*` (kpr-i75-worker, GLM-5.3, yolo, same scratch repo):

- **Worker role**: ordinary-worker prompt completed its task
  (`edit:1`, no reads). Challenged directly — "does the block apply to
  you?" — the model answered: "**No** — the compact-recovery block
  explicitly applies only to the designated Project Runner Host (or an
  outer kaola-delegator host), and states ordinary Workers must ignore
  it entirely, which is my current role." Zero tool calls; never read
  the Skill; never acted as a runner.
- **Host role** (same session, role switched): real `read` of
  `.kpr/skills/kaola-project-runner/SKILL.md` → quoted
  `KPR-SKILL-RELOAD-8842`, then correctly reported it made no
  re-intake, re-claim, or re-dispatch.

Verdict: the scoped block restores the designated Host and does not
turn ordinary Workers into runners — the one-Runner-per-project
invariant holds at model level on real GLM.
