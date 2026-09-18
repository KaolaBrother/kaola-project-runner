# ZCode compact recovery — live verification (Issue #75)

Isolated real-compaction experiment on ZCode 3.12.3 / CLI 0.16.5, driven
through the merged Issue #79 ACP adapter (`kaola-zcode-acp.py` 0.3.3). No
credentials were read, copied, or printed; no global ZCode config or hooks
were touched (user `cli/config.json` kept `hooks:{}` throughout); nothing was
installed to user scope; no other session was touched.

## Fixture

- Scratch Git repo: `/private/tmp/kpr-i75-zcode/repo` (throwaway).
- Planted Skill: `.zcode/skills/kaola-project-runner/SKILL.md` inside the
  scratch repo, carrying reload marker `KPR-SKILL-RELOAD-7931`.
- Runner session: `i75z` → ACP `zcode-1` → native `sess_8000371f-4a04-4494-85a0-95b6e61bd9b9`.
- Mode `yolo` applied at start (`current_mode_update` in `events.jsonl`).
- Storage note: the adapter's env allowlist does not forward
  `ZCODE_STORAGE_DIR`, so the session lived in the runtime's real
  `~/.zcode` store — the runtime's own session data, not a config mutation.
  All inspection of it was read-only (`mode=ro`).

## Sequence and receipts

| Step | Action | Result |
|---|---|---|
| 1 | `start` | session ready, `yolo`, `native_session_identity` = `sess_8000371f…` |
| 2 | `send` "reply READY" | `READY`, `turn_completed` |
| 3 | `send` "remember token ZEBRA-991" | `OK` |
| 4 | `send` `/compact` | `turn_completed`, `final_text:""`, 7 298 ms — summarization turn (usage: 440 output tokens) |
| 5 | `send` "what was the token" | `ZEBRA-991` — manual compact preserved it in the summary |
| 6 | `send` carrier prompt (`KPR-ZCODE-RECOVERY-V1`, re-read Skill, reply with reload marker) | `KPR-SKILL-RELOAD-7931`; `tool_call` `read` on the exact planted SKILL.md path; `agent_thought_chunk` shows the model reasoning about the marker request |
| 7 | `observe` / `capture --tools` / `capture --full` | zero compaction fields anywhere; `context_usage: {size:null, used:null}` |
| 8 | `stop` | `stopped:true`, `agent_exit_code:0`, `residual_pids:[]`, repo clean |

## What this proves

1. **Real manual compaction through the normal prompt path.** `/compact`
   sent as `session/prompt` text produced `context_compaction` timeline and
   `compaction` parts in `db.sqlite` (`trigger:"manual"`, `auto:false`,
   `phase:"standalone_turn"`, `operationId:cmp_d814b072…`,
   `compactReason:"user_requested"`), committed synchronously — see
   `db-compaction-parts.json`.
2. **The Host/Skill-layer carrier works.** Post-compact, one prompt carrying
   the recovery text made the model re-read the installed Skill (real `read`
   tool call on the planted path) and quote a marker obtainable only by that
   read. This is the production mechanism now shipped as
   `references/zcode-compact-recovery.md` with marker `KPR-SKILL-RELOAD-V1`.
3. **Compaction is invisible to the Runner's event surface.** `observe`,
   `capture --tools`, `capture --full` expose no compaction signal;
   `context_usage` is null. Detection for anything other than an
   Agent-requested `/compact` requires the read-only `part`-table diagnostic
   — which stays a diagnostic, not a send gate or ledger.
4. **Facts can survive manual compact** (ZEBRA-991 was retained in the
   summary). The carrier's purpose is re-instruction — the compacted model
   no longer knows to re-read the Skill — not fact recovery.

## Honestly untested

- Auto-compaction live (context-pressure path). Static analysis says it
  writes the same `part`-table record family (`auto:true`), so the
  diagnostic query would see it; the carrier mechanism is identical.
- Carrier behavior on prompts composed outside the Runner (a human typing
  in the ZCode UI). `UserPromptSubmit` would be needed for that coverage —
  kept as documented fallback, not implemented: it costs a user-global
  `hooks.enabled` write the Runner does not need.
- Multi-compaction episodes and carrier repetition beyond one resend.

## Artifacts

- `events.jsonl` — full holder event log (38 events; contains only session
  ids, usage counters, chunk texts, and the scratch file path).
- `db-compaction-parts.json` — sanitized `part`-table extract for the live
  session (record fields only; no message bodies).
