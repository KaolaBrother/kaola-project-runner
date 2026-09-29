# KPR run 2026-09-29: orchestration and prompt gap diagnosis (read-only), revision 2

Seat: `claude-KPR-diag-orchgaps` (claude-code opus/xhigh, read-only). No implementation, tests, issues or commits.
Times are UTC (`Z`). Local time is Z+8. Labels: **PRODUCT** = prompt/template wording; **OUTER** = outer-Agent
execution; **HOST** = Host execution; **UNKNOWN** = transport or model fact these receipts cannot settle.

## Consensus with outer

| # | Outer point | Verdict | Change in this revision |
|---|---|---|---|
| 1 | Already-authorized release/install mechanics may be Host-owned with no mandatory issue or worker; honor user allocation and existing lifecycle. An explicit Host-direct instruction overrides the Skill default. Delete the duplicate row; keep the implementation boundary. | **AGREE** | A1 is now permissive ("may be yours"). The "only compliant reading" claim is withdrawn: it held only while no Host-direct instruction had reached the Host. The owner's 07:24:40Z instruction was replaced in relay by "worker-driven", and the explicit one arrived only at 07:56:09Z. A2 deletes the duplicate row. The top implementation prohibition stays. |
| 2 | A pause covers only its named actions and preserves diagnostics and unrelated work. Urgent affected execution uses the existing exact-session interrupt/cancel. Verify adoption and take no further affected actions; state updates, reports and safe checkpoints stay allowed. Reconcile never-cancel wording. No instant-cancel/undo guarantee and no new stop framework. | **AGREE** | A5, K1 and N1 are narrowed to named actions. N1 says "no undo; reconcile any in-flight result". S3 reconciles `Delegator SKILL.md.tmpl:42` "never restart or cancel in-flight work". |
| 3 | A7: prior success may be evidence, never precedent alone. Keep class/task-fit order, remove the duplicated Elite lean, no blanket Worker preference. | **AGREE** | A7 now reads "(not past success alone)". A8 removes the duplicate lean. No Worker preference is added. |
| 4 | S1 must allow relaying owner-explicit model/seat choices. Forbid inventing allocations, not relaying them. Consolidation never delays an urgent stop. | **AGREE** | S1 now reads "Relay the user's own worker choices; invent none." N2 adds "never delay a stop". |
| 5 | Q1: owner availability confirmation wins over dated or superseded quota evidence. A passed reset does not prove all windows recovered and never restores a revoked Elite grant. No probes, no timers. | **AGREE** | Q1 drops "a passed reset retires it" and now reads "owner-confirmed availability wins". The existing Elite row ("only the user reauthorizes it") already covers revocation. |
| 6 | K2: only a verified same-config rename preserves a grant. Omit if unnecessary. | **AGREE: omitted** | The one rename confusion (F4) was resolved by a single relay. The exact-preset-ID rules (`worker-profiles.md` "Preset IDs in authorization") suffice. |
| 7 | F6: a full outer inquiry sweep differs from answering one permission event with the current owned identity. Keep identity/orphan safety. No unproven allow-always. Reuse still-valid evidence; an affected mutation invalidates it. | **AGREE** | A6 and H3 scope the sweep to Delegator prompts. The permit path already reads that exact seat's live `pending_permissions` (`zcode-host-dispatch.md.tmpl:147-148`), so identity safety stays; orphan safety stays in the sweep. A9 reads "valid facts to reuse". Invalidation already exists in `SKILL.md` step 4 ("reuse invalidated evidence") and in the global contract ("Mutation invalidates affected PASS evidence"). |
| 8 | Fact correction: the post-pause `~/.claude/skills` refresh is an install. | **AGREE: corrected** | F3 now records it as an additional pause-boundary action, with its scope and receipts. No further install and no rollback. The existing text already required relaying rather than installing (F3). |

## Receipt locators

- **Host holder events:** `/tmp/kaola-501/zcode/zcode-KPR-orchestrator-main/906acb94c0d1178e/events.jsonl`. Cited by `cursor` or `request_id`.
- **Outer (Codex) rollout:** `~/.codex/sessions/2026/09/26/rollout-2026-09-26T22-20-10-01a0de16-7ab5-7212-8b72-1b34adb02b3a.jsonl`. Cited by timestamp. It holds the owner's messages and the full text of every outer→Host message.
- **Cursor worker holders:** `/tmp/kaola-501/cursor-cli/cursor-KPR-i{224,225,226,228,230,234}-*/906acb94c0d1178e/events.jsonl`.
- **Other sources:**
  - Archives: `kaola-workflow/archive/issue-222..232`, `issue-234-admin`
  - Heartbeats: `.kaola/heartbeat-prompt.json`, `.kaola/delegator-heartbeat.json`
  - `git log` for 2026-09-29
  - Install receipts: `~/.{codex,zcode,agents,claude}/skills/.kaola-install-receipts/`
- **Installed Skill:** `~/.zcode/skills/kaola-project-runner/SKILL.md` is byte-identical to `skills/kaola-project-runner/SKILL.md` (v0.6.10). The template source is `templates/orchestrator/SKILL.md.tmpl`.

## Summary

| # | Question | Main cause | Strength |
|---|---|---|---|
| F1 | Release/install became #234 + Cursor Elite | OUTER worker-driven directives. PRODUCT has no Host close-out allowance. HOST picked Cursor by precedent. | strong / strong / strong |
| F2 | Self-execution prohibition is overbroad | PRODUCT | strong |
| F3 | Pause request155 not adopted; post-pause installs | HOST non-adoption. OUTER used a plain steer and reported "received" as adopted. PRODUCT has no named-action stop/adoption rule. | strong / strong / moderate |
| F4 | Heartbeat JSON lagged reality | HOST rewrite lag. OUTER shared the stale quota. PRODUCT (quota dating, write timing). | strong / moderate / moderate |
| F5 | Outer handoff mistakes | OUTER | strong |
| F6 | Redundant approval/check loops | Cursor per-command permission (fact). HOST per-event full beats. OUTER gate lists. PRODUCT sweep wording. | strong / moderate / moderate / moderate |
| F7 | #231 scope drift | OUTER issue framing + HOST acceptance after a written cancel. A shared prompt cause is **weak**. | strong / moderate / weak |

---

## F1: Simple release/install became release issue #234 plus a Cursor Elite worker

**Evidence:**
- **07:24:40Z Owner:** "你后合没什么问题，你就让 host 去发布一个新的 release，然后同时给安装一下它" ("if the merge is fine, have the Host publish a new release and install it"). The owner named the Host as the actor, with no worker and no issue.
- **07:25:55Z Outer→Host:** "Once my PASS arrives, you own **worker-driven** release and installation … Normal release issue is authorized if workflow requires."
- **07:36:08Z Outer→Host:** "Own release issue if needed".
- **Precedent (v0.6.9):**
  - 09-28T23:58:37Z: "Once outer PASS arrives, **normal release worker should prepare/publish** exact v0.6.9 … Create normal release issue if needed".
  - 00:55:33Z: "through an appropriate currently authorized worker, normal release issue/lifecycle as needed". This became #225 on `cursor-KPR-i225-release`.
- **Host decision record:**
  - 07:26:06Z thought: "worker-driven **release v0.6.10**".
  - 07:37:18Z: "在一个空闲的 Elite seat 上调度发布" ("dispatch the release on an idle Elite seat").
  - 07:48:06Z: "Use cursor-cli/default (**proven release performer — it did v0.6.9's release run**). Need a release issue: … the v0.6.9 release used issue #225."
  - #225 (00:55:50Z): "owner rule 'prioritize stronger suitable authorized Elite …'" plus "#224 success".
  - Neither thought compares a Worker preset. At 07:48Z codex/luna, devin, dsh and zcode default were all 0 live.
- **Host self-report (08:16:11Z):** "did **not** evaluate Worker-class presets".
- **Owner (07:54:43–08:00:59Z):** "发布为什么要开issue？ … host自己就可以做release和安装啊！ … 无限席位的worker class都是干什么的？" ("Why open an issue for a release? … the Host can do the release and install itself! … What are the unlimited-seat Worker-class presets for?").
- **Outer (07:56:09Z):** "My instruction to create release issue234 and dispatch a release worker was unnecessary overhead."

**Causes:**
1. **OUTER, strong.** The owner's Host-direct instruction was relayed as "worker-driven". This breaks existing Delegator rules:
   - `SKILL.md.tmpl:12-13`: the Host owns worker dispatch.
   - `:52`: "Pass no … scheduling".
   - `:65`: "Do not dispatch workers".
   - `snapshot.md:32`: "Never … select workers".
2. **PRODUCT, strong (enabling).** With no Host-direct instruction reaching it, the Skill's default leads to delegation:
   - `SKILL.md:16-19`: "do not … edit project documentation … or mutate the repository yourself".
   - `:127`: "Self-execute | Off".
   - `:201`: "direct its owning worker to finalize".
   - `:185`: "Give each clear task directly to a suitable authorized worker".
   - An explicit Host-direct instruction overrides that default. It reached the Host only at 07:56:09Z.
3. **HOST, strong.** The seat was chosen by precedent. The ordering in `worker-profiles.md:79-82` ("class responsibility → profile/task fit"; "Worker handles simpler bounded work") was skipped.
4. **PRODUCT + OUTER, moderate (Elite lean).**
   - The heartbeat priority (outer, 09-28T16:51:47Z, after the owner's 16:50:32Z question) is correct as written ("Worker class supports simpler bounded tasks"). The Host applied only its first half.
   - #224 then duplicated the lean into the Defaults row (`SKILL.md:120`), in addition to `:59-64`.
5. **Issue creation, moderate.** It came from the outer's issue permission and the #225 precedent. `SKILL.md:269-271` already allows issue-less tasks.

**Wording:**
- **A1** (`SKILL.md.tmpl:18-19`)
  - Replace:
    ```
    or mutate the repository
    yourself.
    ```
  - With:
    ```
    or mutate the repository
    yourself. Authorized release/install mechanics may be yours: no mandatory
    issue or worker; honor user allocation and lifecycle.
    ```
- **A7** (`:63`)
  - Replace: `profile/task fit, capacity;`
  - With: `profile/task fit (not past success alone), capacity;`
- **A8** (`:109`)
  - Replace:
    ```
    | Allowed CLIs | Five Worker presets are default-authorized (permission, no per-seat/count/priority, outside cap); Elite explicit grant; Expert per-task permission; not a preference over suitable authorized Elite. No authorized task: ask, start no worker, register no heartbeat. |
    ```
  - With:
    ```
    | Allowed CLIs | By class (above). No authorized task: ask, start no worker, register no heartbeat. |
    ```
- **S1** (`Delegator SKILL.md.tmpl:52`)
  - Replace:
    ```
    Pass no per-worker `--repo`, scheduling, or heartbeat instructions.
    ```
  - With:
    ```
    Relay the user's own worker choices; invent none. Pass no per-worker `--repo`,
    scheduling, or heartbeat instructions.
    ```

## F2: The Host self-execution prohibition reads overbroad

**Evidence:**
- **The literal text forbids all release/install mechanics:** `SKILL.md:16-19`, repeated at `:127`.
- **What the Host already did directly:**
  - It created forge issues: #225 at 00:56:42Z and #234 at 07:48Z.
  - It rewrote the heartbeat each beat.
  - It made the #234 administrative archive commit `3a218f02` (08:06:56Z).
- **Once explicitly allowed** (07:56:09Z / 08:00:57Z):

  | Path | Window | Outcome |
  |---|---|---|
  | Host-direct | 08:02:40–08:08:00Z (≈5.5 min) | Merge R, tag, pin P, publish, admin close/archive, install |
  | Worker | 07:49:26–08:01:34Z (≈12 min) | Reached only content commit R `5f7c9d9d` |

**Cause:** PRODUCT, strong.

**Wording:**
- A1 (above) is permissive and keeps the implementation boundary.
- **A2:** delete `SKILL.md.tmpl:116` `| Self-execute | Off unless the human explicitly allows it. |` (duplicate of the top paragraph).

## F3: Pause request155 was not adopted before publication; further installs after the pause

**Timeline (Host `events.jsonl` unless noted):**

| Time (Z) | Event |
|---|---|
| 08:04:16 | Host: "Tag `v0.6.10` published at R". |
| 08:04:17.2 | Outer request154 (diagnostic assignment), which includes "…HOST-DIRECT release/install, **which continues**". Injected 08:04:18. |
| 08:04:18 | Owner: "发布先暂停" ("pause the release first") (outer rollout). |
| 08:04:49.0 | Outer sends a **plain `steer`**: "URGENT OWNER STOP BOUNDARY … PAUSE RELEASE NOW" (request155, turn 151). Pin P `1e2cee55` commit time 08:04:49 (tool call 33299–33302 ends 08:04:52). |
| 08:04:52 | `steer_result` 155: `injected`, `steer_consumed=true` (`agent-confirmed`). |
| 08:05:30 | Host thought "Next: GitHub release". No pause reference. |
| 08:05:30.9 | Outer to owner: "暂停指令已被 Host 确认接收" ("the Host has confirmed receipt of the pause"). |
| **08:05:36** | GitHub release v0.6.10 published. |
| 08:06:37–08:07:02 | #234 closed, ledger rewritten, archive commit `3a218f02`. |
| 08:06:40 | Outer detects the deviation. It reads docs until 08:09:14. |
| 08:07:24–08:07:29 | Installs into `~/.codex`, `~/.zcode` and `~/.agents` skills (receipts `installed_at` 08:07:26/28/29Z). Main Skill `content_sha256` `cf5fdbfca789…`. |
| 08:09:51 | Outer `steer --steer-mode interrupt` → `steer_resent_without_interrupt` (turn ended 08:09:31), new turn 157. |
| 08:10:11 / 08:10:22 | Host: "已确认暂停" ("pause confirmed"). JSON marked PAUSED. |
| **08:14:47–08:15:20** | **Additional install after pause adoption, into `~/.claude/skills`.** Complete root, 11/11: ten worker Skills (`installed_at` 08:14:47Z) plus `kaola-project-runner` (08:15:20Z). `method: copy`, referrer `claude-code`, source `…/kaola-project-runner/skills/*` checked out at the frozen v0.6.10 tag. The main Skill `content_sha256` `cf5fdbfca789…` is identical to the 08:07Z installs. The checkout then returned to `main` (Host 08:16:11Z). The Host labelled it "不属于发布/安装操作" ("not a release/install action"). **That is incorrect: it is an install inside the paused scope.** |

- The pause was otherwise followed from 08:10Z: no further tag, publish or install, and no rollback.
- The diagnostic dispatch correctly continued, because the release pause does not cover it.

- **Same non-adoption pattern earlier:**
  - request149 was injected at 07:56:21Z. The Host kept approving worker inspections at 07:56:44Z, 07:57:25Z and 08:01:08Z, and acted only on request152 (08:01:21Z).
  - Its own 08:01:17Z thought shows request149 was visible: "appeared in the system prompt context".
  - request153 was answered only at 08:16:11Z.

**Causes:**
1. **HOST, strong.**
   - An injected, visible pause was not applied before the next affected action (publish, then archive, then install).
   - The 08:14Z `~/.claude/skills` refresh went against existing text that already covers this case:
     - `docs/api.md:564-566`: "A Host that cannot run the authorized install itself relays this exact route to the Delegator or operator and keeps its task and seat".
     - `host-startup.md.tmpl:81-83` says the same.
   - Under an install pause, relaying was the compliant path. No new wording is needed for this.
2. **OUTER, strong.**
   - It used a plain steer for a stop, 31 s after an opposing "continues" message.
   - It reported injection as adoption (08:05:30.9Z). Outer 08:10:30Z: "此前把'消息已送达'当成暂停落实…这是我的问题" ("I treated 'message delivered' as the pause being carried out … that is my fault").
   - It spent ≈3 min in docs before interrupting. The 08:07Z installs fell inside that window.
3. **PRODUCT, moderate.**
   - **Delegator side:** `SKILL.md.tmpl:58-59` names no stop route and does not say `injected` is not adoption.
     - `SKILL.md.tmpl:42` says "never restart or cancel in-flight work", which conflicts with an owner-directed stop.
     - `snapshot.md:39-43` has the right confirmation model, but only for `day_end`.
   - **Host side:** `SKILL.md:148-150` and `heartbeat-skeleton.txt:14` ("after each natural beat") give a pause no immediate, named-action effect.
4. **UNKNOWN.** How ZCode's `guide` delivery presents steer text to the model. request152 was adopted in 11 s; requests 149, 153, 154 and 155 were not.
   - Worker `steering.md:24`: "adoption by the model is a separate question".

**Wording** (no new stop framework; no cancel or undo guarantee):
- **A5** (`SKILL.md.tmpl:138-139`)
  - Replace:
    ```
    A report-only
    request disables execution actions.
    ```
  - With:
    ```
    A report-only
    request disables execution actions; a stop or pause, only its named actions
    from your next tool call.
    ```
  - State updates, reports and safe checkpoints stay allowed. Unrelated work and diagnostics continue.
- **K1** (`heartbeat-skeleton.txt:14`)
  - Replace: `用户或 Delegator 的变更以单独消息到达，确认后写进对应字段；`
    ("user or Delegator changes arrive as separate messages; once confirmed, write them into the matching field;")
  - With: `用户或 Delegator 的变更以单独消息到达，确认后当拍写进对应字段；停止/暂停先记入，只停其所指动作；`
    ("…once confirmed, write them into the matching field in the same beat; a stop/pause is recorded first and halts only the actions it names;")
- **S0 + S2** (`Delegator SKILL.md.tmpl:58-59`)
  - Replace `Relay user changes to the same Host:` with `Relay user changes to this Host:`.
  - Replace `` `--no-wait` admission and Host `end_turn` are not delivery. `` with `` Admission, `injected` or `end_turn` isn't adoption. ``
- **S3** (`Delegator SKILL.md.tmpl:42`)
  - Replace: `never restart or cancel in-flight work.`
  - With: `never restart or cancel in-flight work unless the owner stops it.`
- **N1** (`snapshot.md:45-46`)
  - Replace:
    ```
    existing close-out and exact-stop rules; confirm the result before disabling
    recurrence.
    ```
  - With:
    ```
    existing close-out and exact-stop rules; confirm the result before disabling
    recurrence. An owner stop or pause of named actions goes at once by
    `steer --steer-mode interrupt` (no undo; reconcile any in-flight result) and is
    confirmed like `day_end`: Host acknowledgment plus no later affected action in
    its receipts; `injected` is not adoption. Unrelated work continues.
    ```

## F4: Stale state in the heartbeat JSONs

**Evidence:**
- **JSON cleanup lag of ≈64 min** across outer directives at 01:58:33Z, 02:01:50Z and 03:02:43Z ("the saved file still contains those exact stale entries despite prior confirmed steering").
- **Wrong rows (outer 06:59:07Z, item 5):** "opus-xhigh is GRANTED but incorrectly under revoked; ungranted new Claude default must not be an authorized row … false inference that OpenCode failed for the same cause as DSH".
- **Release ownership still delegated at 08:00:57Z:** "your JSON still delegates release/install to it".
- **Pause not recorded until 08:10:22Z** (F3).
- **Stale quota in both JSONs:**
  - Delegator `known_resource_limits` and Host `quota_notes` both said "quota exhausted".
  - The outer's own request154 (08:04:17Z) restated it.
  - The Host blocked the diagnostic at 08:10:31Z.
  - Owner at 08:12:31Z: "claude is available, remove stale information". Residual clauses were still present at 08:14:12Z.
- **History the skeleton forbids** (`heartbeat-skeleton.txt:5,15`) remains in the current Host JSON:
  - "upstream outages x2 today", "turn-level failure … NO evidence attributing it to the DSH route issue".
  - A stale row state: "0 live -> dispatching diagnostic seat".

**Causes:**
- **HOST, strong.** `SKILL.md:146-149` and skeleton `:15-17` already require replacement from fresh facts.
- **OUTER, moderate.** The same stale quota was in the outer's own JSON and directive.
- **PRODUCT, moderate.** `quota-packages.md:53` keeps exhaustion evidence with no date and no owner-override clause. K1 covers the write-back timing.

**Wording:**
- **Q1** (`quota-packages.md:53`)
  - Replace: `keep the evidence and any known pool/reset facts.`
  - With: `keep dated evidence, pool/reset; owner-confirmed availability wins.`
  - No probe or timer. A passed reset proves no recovery and never restores a revoked grant; the Elite row already covers that.
- K1 (F3).
- K2 is omitted (consensus point 6).

## F5: Outer handoff mistakes

**Evidence:**
- **#228: four serial specs** (02:39:06Z, 03:12:10Z, 03:15:55Z, 03:35:36Z).
  - The 03:12:10Z relay ("Sonnet remains Worker Class … xhigh … TWO … seats") was superseded by the owner 1 s later (03:12:11Z).
  - Worker ledger n=3: "after the intermediate xhigh Sonnet request".
  - #230 re-designed the same presets about 1 h after commit `1e8644a8` (04:51Z).
- **#230: six body edits and relays in 16 min** (05:44:45–06:01:01Z).
  - Three Cursor worker turns were cancelled by interrupt (05:52:54Z, 05:56:13Z, 05:56:50Z).
  - The outer added a constraint the owner never stated at 05:58:28Z: "Cursor Opus … remain unchanged", labelled "FINAL". The owner reversed it at 05:59:33Z.
- **Consumption reported as delivery or adoption:** 02:01:50Z, 08:00:57Z and 08:05:30.9Z (F3).
- **Worker-driven release directives:** see F1.
- **#231:** see F7.

**Causes:**
- **OUTER, strong.** The existing rule was not followed: `Delegator SKILL.md.tmpl:24-25` "apply only the user's latest change".
- **PRODUCT, weak.**

**Wording:**
- S1 (F1).
- **N2** (`snapshot.md:31`)
  - Replace: `send one concrete correction to that Host, replace stale facts.`
  - With:
    ```
    send one concrete correction to that Host (the user's latest wording,
    consolidated, no constraint they did not state; never delay a stop), replace
    stale facts.
    ```

## F6: Redundant approval and check loops

**Permission counts per Cursor seat** (worker holder `request_permission` / `permission_answered`):

| Seat | Requests | Answered |
|---|---|---|
| #224 | 5 | 5 allow-once |
| #225 | 14 | 14 allow-once (00:58:44–01:21:42Z) |
| #226 | 20 | 20 allow-once |
| #228 | 13 | 13 allow-once |
| #230 | 11 | 10 allow-once (req 0 lost to interrupts) |
| #234 | 8 | 7 allow-once + 1 reject-once (07:52:23–08:01:52Z) |

- **Other platforms:** Droid, Codex, Grok, Claude Code, OpenCode and ZCode raised 0.
- **Mostly read-only commands:** #234 7/8 (the 8th was `git tag -a v0.6.10`); #225 at least 9/14.
- **Each permission was a full Host beat, with a repo sweep:** "swept:" at 07:52:48, 07:55:51, 07:56:44, 07:57:25 and 08:01:08Z.
- **Repeated checks:**
  - "v0.6.10 free" was verified four times (Host 07:48:09Z, worker req 0, Host 08:02:42Z, Host 08:03:27Z).
  - "rejected #231 absent" was verified at least five times (Host 07:48:09Z, worker reqs 2, 4, 5, 6).
- **Gate list pushed by the outer (07:25:55Z):** "Verify platform pins/adapters, R/P/tag … do not publish the rejected earlier231".

**Causes:**
1. **Platform fact, strong.** Cursor ACP (`platforms/cursor-cli.yaml:40`, `--yolo`) asked once per shell command. `README.md:527-531` says only that it "may still arise".
2. **HOST, moderate.** It ran a full sweep and beat per event, and re-verified facts it had already established.
3. **OUTER, moderate.** It sent gate lists with no marking of already-verified facts, and `sweep=every beat` in its handoff.
4. **PRODUCT, moderate.**
   - `SKILL.md:34` "sweep first in every beat" and `handoff.md.tmpl:141` "sweep=every beat" conflict with `host-startup.md.tmpl:101-103` ("every beat a Delegator opens").
   - The permit path (`zcode-host-dispatch.md.tmpl:147-148`) already reads that exact seat's live `pending_permissions`. That is its owned-identity check, so the sweep adds nothing for a permission event.
5. **UNKNOWN.** Whether Cursor ACP honors `allow-always` for a session, and whether `--yolo` is meant to suppress `request_permission`. No allow-always wording until an existing receipt shows it.

**Wording:**
- **A6** (`SKILL.md.tmpl:34`)
  - Replace: `the repo sweep first in every beat`
  - With: `the repo sweep first in each Delegator prompt`
  - Affected test: `tests/contract/test-generated-skills.py:594`. Orphan and identity safety stay in that sweep.
- **H3** (`handoff.md.tmpl:141`)
  - Replace: `sweep=every beat:`
  - With: `sweep=this prompt:`
- **A9** (`SKILL.md.tmpl:246-247`)
  - Replace:
    ```
    Its prompt should name the authorized
    scope,
    ```
  - With:
    ```
    Its prompt should name the authorized
    scope, valid facts to reuse,
    ```
  - Invalidation after an affected mutation is already required by step 4 and the global contract.

## F7: #231 scope drift

**Evidence:**
- **Owner ask** (06:33–06:34Z): "安装的时候自动给配置好就行" ("just have it configured automatically at install").
- **Issue as written by the outer** (#231 at 06:34:57Z): "Complete the DSH default setup … configure the declared default". This is provider provisioning.
- **Owner narrowing to ACP-protocol-only** (06:46–06:48Z).
- **Three outer corrections in 2 min:** 06:47:09Z, 06:47:49Z (cancel) and 06:49:16Z (harness-only).
- **Worker commit** `b24e048d` at 06:47:27Z, before the cancel.
- **Host handling:**
  - Host steers 121 and 123 got outcome `written`.
  - The Host reported "#231 主机评审：PASS" ("Host review of #231: PASS") at 06:49:30Z, judged against the superseded clarification.
  - It also accepted a #229-caused `test-issue-118` failure as "pre-existing".
- **Churn:** the outer rejected it at 06:59:07Z. Then `eeace4c2` (−76 README), `9578cf89` (+24), and the owner-directed #232 folded the note into `docs/api.md` (`acd58cfc`).

**Causes:**
- **OUTER, strong.**
- **HOST, moderate.** It accepted a candidate after a written cancel, the same mechanism as F3.
- **Shared prompt cause, weak.** Covered by A5 and N2. No separate wording.

---

## Byte budgets (checked against current files)

| Surface | Current / budget | Edits | After |
|---|---|---|---|
| main Skill | 17405 / 17408 | A1 +118, A2 −62, A5 +66, A6 +11, A7 +25, A8 −179, A9 +22 | 17406 |
| Delegator Skill | 4091 / 4096 | S0 −4, S2 −8, S1 +50, S3 +26, S4 −86 | 4069 |
| `handoff.md` | 8179 / 8192 | H3 +1 | 8180 |
| `snapshot.md` | 3125 / 8192 | N1 +283, N2 +96 | 3504 |
| `quota-packages.md` | 8173 / 8192 | Q1 +18 | 8191 |
| `heartbeat-skeleton` | 7998 / 8192 | K1 +55 | 8053 |

- **S4 offset for S1 and S3:** replace `Delegator SKILL.md.tmpl:69`
  ```
  KPR update: [host-platforms.md](references/host-platforms.md#kpr-updates); a notice proves no updated install or loaded guidance, authorizes no install/restart.
  ```
  with
  ```
  KPR update: [host-platforms.md](references/host-platforms.md#kpr-updates).
  ```
  The deleted clause duplicates `host-platforms.md.tmpl:59-60`.
- **Tests that assert changed text:** only `test-generated-skills.py:594` (A6).
- **Asserted phrases these edits keep:**
  - `test-issue-88-permission-defaults.py:203`
  - `test-issue-94-zcode-native-skill-entry.py:218-222`
  - the "Allowed CLIs" marker
- **Not proposed:** any new mechanism (classifier, timer, stop framework, adoption detector, benchmark, schema), `allow-always` guidance, K2, or a blanket Worker preference.

This report file is untracked and not gitignored. Do not stage it.

**Consensus status:** all eight outer points are AGREE: point 6 by omitting K2, point 8 by fact correction. There is no DISAGREE and no open disagreement. See the table at the top.
