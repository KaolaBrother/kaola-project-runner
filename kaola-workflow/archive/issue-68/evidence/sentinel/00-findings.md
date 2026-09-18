# Live ACP validation sentinel — candidate 54bc864

One isolated ACP session read the candidate Skill and skeleton and produced its own compacted
heartbeats. It was never shown `S*_AFTER` or `S*_NEXT`; the only inputs were the candidate files and
the three raw `before` prompts with their user events. **This is still single-worker
self-verification** — the same worker that wrote the candidate designed the inputs and judged the
output. It is behavioral evidence about the prompt, not an independent review.

## Session facts

| | |
|---|---|
| Transport | ACP (manifest default), via this repo's `claude-code-kaola-project-runner` |
| Session | `kaola-issue68-heartbeat-sentinel`, ACP session `92a16be88bcec68d8803c052de7f9d03` |
| Model | requested `Opus High` from `runner-default`, resolved `opus` effort `high`, Fast `off` (never requested on) |
| CLI | `/opt/homebrew/bin/claude` 2.1.272, bridge pin `6c20f28`, protocol 1 |
| Repo | `/private/tmp/kw68-sentinel` — a scratch dir holding only the two candidate files and the scenario input. No real project, no account-quota action, no scheduler, no heartbeat registered, no worker dispatched |
| Turn | one `send`, `mutation_status: completed`, `stop_reason: end_turn`, 153 s, 4 tool calls, 0 failed, `files_changed: 0` |
| Stop | exact-session `stop`: `stopped: true`, `agent_exit_code: 0`, `residual_pids: []`, `swept_child_pgids: []`; no process or tmux session by that name remains |
| Sentinel marker | the reply ends with `KW68-SENTINEL-DONE`, so the transcript is complete, not truncated mid-answer |

The `send` receipt's `final_text` came back with `final_text_truncated: true` (the receipt is
bounded by design). The full 18 048-byte reply in `03-raw-reply.txt` was reconstructed from the ACP
event log's `agent_message_chunk` events, which is also why `06-acp-events.jsonl` is kept.

## Real read evidence

From the event log, the session's own tool calls (cursors 16–18):

```
cat candidate/heartbeat-skeleton.md        status: completed
cat candidate/kaola-project-runner-SKILL.md status: completed
cat scenarios.md                            status: completed
```

sha256 of what it read: skeleton `b02ce1d3…b42c19c`, Skill `7228b031…6ff6a4f1e5` — byte-identical to
the candidate's rendered `skills/kaola-project-runner/references/heartbeat-skeleton.md` and
`SKILL.md` at 54bc864.

## What its own output shows

**Superseded values dropped.** Scenario 1's `Codex ×2（账户额度本周剩余 20%）` and `Claude Code 未授权`
are gone. Scenario 2's `并发 4（用户 2026-09-17 上调）` is gone, replaced by
`并发 2（本拍用户确认，唯一有效值）` — and it wrote "唯一有效值" unprompted.

**The three quota kinds stayed separate.** Scenario 2 came back as
`Codex ×3（已授权工人数）；并发 2（本拍用户确认）；token 预算 本周 8M` — three values, none fused.
Scenario 1 goes further than my fixture did: it kept `并发上限 2` because the user said "其他不变",
then wrote `当前已授权工人 1，故实际并行 1`, separating the cap from the head count.

**Inert history dropped.** Scenario 1 lost the 429 retry, the Cursor mismatch and the abandoned plan
A. Scenario 3 lost the transient tmux reconnect and the superseded plan B, and collapsed the
thrice-repeated project description to one line.

**In-flight locators and unfinished duties survived.** Every scenario carries the session name,
worktree path and Issue of each live worker. Scenario 1: `（在飞；额度下调不取消该任务，保留其定位与剩余收尾职责）`.
Scenario 2 keeps all three workers with `并发下调不取消、不丢弃在飞任务`. Scenario 3 keeps
`#109 的 archive/sink 未完成` and — correctly — keeps the "already merged" fact attached to it as the
pointer that duty needs, while dropping the duplicate narration of the same merge.

**No unauthorized platform switch.** Scenario 1 moved to Claude Code ×1 only because the user said
so; no scenario reached for an unauthorized CLI.

**Acted in the same beat.** Scenario 2's next step is "本拍立即按并发 2 执行：不再新开会话、不补派新工作,
A/B/C 三个在飞任务全部保留不停" — it re-planned immediately and explicitly refused to cancel to fit
the new ceiling, which is the exact failure mode Issue #68 names.

**Per-host terminology, read cold.** Answer C, from a session that had never seen this discussion:
Codex from its own timer at the heartbeat interval; Grok Bot from the single Routine on that Bot
conversation; ZCode Host event-driven with no Routine/cron/sleep, `KAOLA_ACP_HEARTBEAT_HOST` exported
at worker start and a pass delivered on each worker termination or turn-end idle. It then stated
**"不是同一个文件实现"** on its own and named the ZCode `.kaola/heartbeat-prompt.json` `body` carrier
while leaving Codex and Grok Bot on their existing timer carriers.

## Where it diverged from the hand-written fixtures — reported, not hidden

1. **Scenario 1 concurrency.** My fixture's `after` said `并发 1`. The sentinel kept `并发上限 2` and
   argued from "其他不变". The sentinel is right and my constant encoded an assumption the rule does
   not make: the user replaced the platform, not the concurrency. This is the clearest demonstration
   of why the outer coordinator was right that the hand-written constants are not acceptance
   evidence.
2. **Scenario 1 next step.** My fixture said the Codex session is kept and not stopped. The sentinel
   said: dispatch nothing further to it, and *after* verifying its in-flight output has landed and
   its close-out duty is handed over, stop that exact session. That is not a mistaken cancel — it
   preserved the deliverable and the duty first, and the Skill separately requires stopping an idle
   session with no executable authorized work, and states that session stop, acceptance, merge and
   closure are different facts. I read it as compliant, and I am recording it because a stricter
   reader might want to look at it.

No scenario produced a contradictory quota pair, dropped a locator, dropped an unfinished duty,
switched platform without authorization, or cancelled live work.

## Cost note

Each written-back heartbeat reproduces the full stable skeleton, per the keep-list's
"稳定的骨架规则". That is what the rule asks for, and it means the prompt does not shrink much in
absolute size — what shrinks is the stale project state. If the outer coordinator wants the
skeleton carried by reference instead, that is a separate design question and a separate issue, not
a defect in this candidate.
