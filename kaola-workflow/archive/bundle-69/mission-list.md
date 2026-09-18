# Issue #69 — ZCode Host event wake: remaining live evidence legs

Scope (from issue body + latest comments): #65/#69-comments already live-proved real ZCode Host
+ inner ZCode Worker + Codex Worker dual-delivery, batch flush of two staged events, exact-stop
isolation, and full idle→delivered→confirmed→terminated chains. Remaining legs still offline-only:

- real `turn_failed` (ACP turn failure / agent crash — not a tool-call non-zero exit)
- resume of unconfirmed events → re-delivery after holder restart
- duplicate-event dedup (real duplicate delivery, not the batch-flush shape)

Constraints: ACP-only; isolated local ZCode sessions/projects only; no global config/credential/
other-session changes; prior isolated probe hit `session/create app-server exited` — if it
reproduces, bounded diagnosis + report, never fake as live. If no defect is found, production code
stays untouched. Frozen evidence + candidate SHA go to outer review; no finalize/push/close before
ACCEPT. Do not touch #65 archive or issue-67/70/73/74 folders/worktrees.

| item | status | dispatched | result |
|---|---|---|---|
| Study ZCode host event contract impl + offline tests + #65 archived live evidence; write bounded probe plan for the three legs | done | inline, main context | Mechanism mapped end-to-end: `on_prompt_response`→`turn_failed`→idle event `reason=outcome=turn_failed`; agent exit→`terminated`+`process_exited`; `op_worker_event` dedups identical pending IDs (`duplicate:true`); `_restore_worker_events` rebuilds unconfirmed events from the append-only log on resume. Probe plan: kill app-server mid-turn for real turn_failed; kill/restart host holder for resume leg; identical carrier re-send for dedup leg. |
| Live leg A: real `turn_failed` staged → delivered → acked via real ZCode Host + ACP worker | BLOCKED | inline, isolated probe `.kw/verify-69-legs/` | UNPROVABLE on installed ZCode 3.12.3/0.16.5. Wall 1: `app-server --stdio` exits at spawn (provider-config resolution bug; adapter allowlist strips the env bypass). Wall 2 (via project-local entry shim, `KAOLA_ZCODE_ENTRY` — the one allowlisted env): real adapter's `session/create` → `ZodError: Unrecognized key "runtimeModel"` — the overlay is dead protocol in 0.16.5; adapter v0.3.0 has no retry. No session can materialize → no real turn → no real turn_failed under the holder. Offline-covered only. |
| Live leg B: unconfirmed staged events re-delivered after holder resume/restart | BLOCKED | inline, same probe | UNPROVABLE — same wall 2; `--resume`/`load` also dies (`setModel` wants string model; registry empty; `reregister_provider` raises). Offline-covered by `test_resume_redelivers_unconfirmed_events` (fake server) only. |
| Live leg C: real duplicate event dedup (same event delivered twice → single ack/consumption) | BLOCKED | inline, same probe | UNPROVABLE end-to-end — staging needs a live host but delivery/confirm needs a working turn. Offline-covered by `test_bounded_queue_dedup_and_single_batch_flush` only. |
| Freeze evidence bundle (cursors/receipts/session identity/exact-stop residual[]) + candidate SHA; report which legs proven vs unprovable to outer review | done | inline | `.kw/verify-69-legs/evidence/00-diagnosis-report.md` — both walls root-caused and receipted through the real stack (holders `4532ee51…`, `c85fa04d…`; ACP `zcode-1`; stops `residual_pids: []`) plus raw-wire probes (bare create → `sess_8fb5a8e6`; send → real `turn-failed`/`Select a model`). Candidate `3dd7e5eb5c4efe679ffbf4717307bf74866e5463`, worktree clean, no production code touched. Runtime defect characterized for reviewer (same walls Issue #74 hit; fix is #74-class, not #69). Awaiting outer ACCEPT. |
| Post-#79 retry — live leg A: real `turn_failed` staged → delivered → acked | done | inline, isolated scratch `.kw/verify-69-legs/legA/` | **live-proven** on `b40813f`. Worker app-server killed under live adapter → real ACP error `{-32603 "Broken pipe"}` → holder `turn_failed` → host log `idle/14 outcome=turn_failed` staged(28)→delivered(29)→confirmed(36); baseline `idle/13` and `terminated/15` chains complete; both stops `residual_pids:[]`. Host `zcode-kaola-i69a-host` `sess_59a7fe78…`, ACP `zcode-1`. |
| Post-#79 retry — live leg B: unconfirmed event redelivery after holder resume | done | inline, isolated scratch `.kw/verify-69-legs/legB/` | **live-proven** on `b40813f`. `idle/19` staged(107) → holder force-stopped unconfirmed (108) → `start --resume zcode-1` → `worker_event_restored`(109) → redelivered(110) → confirmed(129); `terminated/20` chain 130→131→139; all stops `residual_pids:[]`. First attempt (`idle/13` 46/47/58) lost a ~4.4s timing race — discarded, not claimed. Side finding: faithful native-session `resume` fails on real 3.12.3 (`session/read` message-list shape → `hydrate_settings` recovers no model; `runtimeModel` dead protocol; account `setModel` without provider re-registration) — real adapter resume defect, documented in report, outside evidence scope. |
| Post-#79 retry — live leg C: duplicate event dedup, single consumption/ack | done | inline, isolated scratch `.kw/verify-69-legs/legC/` | **live-proven** on `b40813f`. Real worker event `idle/14` staged(17) on busy host → byte-identical carrier replay on host socket → raw reply `{"duplicate":true,"pending":1}` → single lifecycle delivered(150)→confirmed(169). Post-ack identical replay → `staged:true` → second lifecycle 170/171/177 (dedup spans pending window only, at-least-once). `terminated/15` 178→185. Both stops `residual_pids:[]`. |
| Post-#79 evidence freeze + outer-review report | done | inline | `.kw/verify-69-legs/evidence/20-post79-live-legs-report.md` + raw receipts/logs under `legA|legB|legC/{evidence,records}` — all three legs live-proven on candidate `b40813f04f6c5faf00ef1866efe343dad4614253` (worktree `workflow/bundle-69` clean); production untouched; adapter resume defect reported for separate triage. Awaiting outer ACCEPT before any finalize/archive/sink. |

## Why the legs are blocked (one-paragraph handoff)

The adapter↔runtime contract broke at ZCode 3.12.3/0.16.5: `runtimeModel` was removed from the
wire schema (zero occurrences in the bundle) and the app-server spawn can't resolve its own
provider config next to `Resources/glm/zcode.cjs`. Issue #70's real turns at 17:12–18:36 today
predate the 19:08 desktop relaunch that emptied `~/.zcode/v2/provider_config.json` and pulled the
runtime provider layer; since then every headless create hits the same walls Issue #74 documented
(`Select a model before continuing`). Continuing requires either the #74-class adapter+provider-
config work or a machine state that no longer exists — outside this run's evidence-only scope.
