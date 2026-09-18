# Zcode Orchestrator external entry and Grok Bot carrier migration

## item
Generate the thin shared Zcode Orchestrator Skill (`zcode-orchestrator`) from templates via the renderer, with a small justified budget and no second engine
status: done
dispatched: self; output lands in templates/zcode-orchestrator/, templates/budgets.json, scripts/render-skills.py, and generated skills/zcode-orchestrator/
result: PASS. `skills/zcode-orchestrator/` is renderer output (SKILL.md 2308 B). `external_skill_bytes` 4096; existing ceilings unchanged.

## item
Migrate the Grok Bot bridge, verifier, installer discovery, and host docs so the account Skill loads `zcode-orchestrator` after bind+locator; do not auto-rename, restart, or cancel in-flight old entries
status: done
dispatched: self; output lands in templates/grok-bot/, hosts/grok-bot/zcode-orchestrator.md, scripts/kaola-grok-bot-verify.py, docs/grok-bot-host.md
result: PASS. Account Skill is `zcode-orchestrator.md` (2408 B). Old `kaola-project-runner.md` withdrawn from the generated bundle; INSTALL says not to rename/restart/cancel in-flight old account Skills.

## item
Retarget Project Runner consuming entries to Codex, generic, and ZCode; drop Grok Bot as a direct Project Runner host and Routine carrier; do not raise existing budgets or duplicate #73 root binding
status: done
dispatched: self; output lands in templates/orchestrator/SKILL.md.tmpl, heartbeat-skeleton.txt, generated main Skill
result: PASS. Main Skill 16256 B / 17408. Grok Bot Routine carrier removed. No canonical-root binding mechanism added (#73 stays queued).

## item
Install `zcode-orchestrator` for Codex and generic destinations (skip with `--no-orchestrator`); keep nine workers and standalone compatibility; freeze `templates/grok-golden/`
status: done
dispatched: self; output lands in scripts/install-local.sh and installer contract tests
result: PASS. Codex and `--skills-dir` install both control-plane Skills; ZCode/Claude/Cursor/Devin do not get the external Skill; `--no-orchestrator` skips both. grok-golden git diff empty.

## item
Add contract and minimal real isolation verification (original task/quota handoff, Host start/resume, inner Runner load, allowed worker, end_turn event wake) with receipts; do not claim live Grok Bot UAT
status: done
dispatched: self; output lands in tests/contract/test-issue-74-zcode-orchestrator.py and kaola-workflow/issue-74/evidence/
result: PASS. 37 assertions. Original `ISSUE74-TASK` text is in `evidence/04-host-rpc-prompts.json`. Live Grok Bot UAT not executed. `scripts/validate.sh` PASS.

## item
Land README four-tier entries and AGENTS.md short principles under the final name Kaola-Delegator (`kaola-delegator`), with a freeze SHA for other in-flight agents
status: done
dispatched: self; output lands in README.md, AGENTS.md, and a freeze commit on workflow/issue-74
result: PASS. Freeze SHA `380ca2b25fef708bf038dc8fb010c146718dcf95`. README four-tier table and AGENTS.md Layered entry use Kaola-Delegator / kaola-delegator. render --check PASS.

## item
Rename the generated external Skill, Grok Bot bridge, installer, and tests from zcode-orchestrator to kaola-delegator so documents match the candidate
status: done
dispatched: self; output lands in templates/kaola-delegator/, skills/kaola-delegator/, hosts/grok-bot/kaola-delegator.md, renderer/installer/tests
result: PASS. Same freeze SHA. No leftover zcode-orchestrator product. Installer/tests/bridge follow kaola-delegator.

## item
Fix Delegator handoff recover/send: live Host continues in place; busy uses existing send/steer receipts; stopped Host resumes only with attested native sess_*; never --continue-guess
status: done
dispatched: self; output lands in templates/kaola-delegator/ and generated skills/kaola-delegator/
result: PASS at `f78ddf31e3730f1ffa91d370896e70482b43a4b3`. Handoff forbids `--continue` guessing; busy path names prompt-in-progress and existing steer. Live attach proven via status on the original Host. Real production stop-then-`--resume` is not claimed.

## item
Persist the A→B continuation record (Runner session, acp_session_id, native sess_*) from real receipts and prove live attach plus honest cannot-resume
status: done
dispatched: self; output lands in handoff.md (`.kaola/delegator-host.json`) and evidence/01b-continuation.json
result: PASS. Isolation run stored session `zcode-KPR-orchestrator-a0f4eb`, `acp_session_id=zcode-1`, `native_session_id=sess_fake1` from the fake Host events, not from session_meta. Missing native id remains cannot-resume. No registry/lock added.

## item
Use standard Host session names `zcode-<PROJECT>-orchestrator-<purpose>`, keep #72 worker names, and detect a missing ZCode Runner instead of claiming the thin entry is ready
status: done
dispatched: self; output lands in handoff.md, SKILL.md, install-local.sh, tests
result: PASS. Host example `zcode-KPR-orchestrator-main`; worker example `zcode-KPR-i74-…`. Installer skips `kaola-delegator` when `--platform` omits zcode. Skill stops if the ZCode Runner is missing.

## item
Fix continuation timing and old-Host adoption: write a provisional current pointer immediately after a successful Host start (native sess_* may be absent), fill sess_* from the identity event after the first handoff, let Agent B live-attach in that window or report cannot-resume if already stopped, and adopt an in-flight Host with a precise trusted locator even when its name is not the new form — never start a second orchestrator because the new HOST name was missing
status: done
dispatched: self; output lands in templates/kaola-delegator/references/handoff.md.tmpl, templates/kaola-delegator/SKILL.md.tmpl, tests/contract/test-issue-74-zcode-orchestrator.py, and kaola-workflow/issue-74/evidence/ (docs freeze 380ca2b left in place)
result: PASS at `6e5c33380c29ddab0e0859a8898ae7043947936b`. Recover step 5 writes `$RECORD` immediately after start; native id may be absent. First handoff fills `sess_*` from the identity event. Live attach before first prompt proven (`01c-live-attach-before-prompt.json`). Nonstandard live Host `zcode-KPR-legacy-*` adopted with no second start (`15-old-host-sessions.json`). Fake isolation does not claim start→prompt→native→A/B live→stop→`--resume sess_*`. Docs freeze `380ca2b` unchanged.

## item
Safely rebase workflow/issue-74 onto current main `1f876661` (includes #72): keep #72 archive, tests, issue-scoped naming and host-startup worker examples, and keep #74 Delegator semantics; do not touch #67/#70/#73 worktrees
status: done
dispatched: self; output lands on workflow/issue-74 after rebase onto origin/main; conflict resolutions in templates/orchestrator/ (host-startup + SKILL) and generated skills/
result: PASS. Rebased onto `1f876661`. HEAD `a071c86124b868d857a6de8f1e86cfb467aee361`. #72 archive, `test-issue-72-session-naming.py`, and `codex-KT-i274-parser` + issue-dispatch kept. host-startup section B still points at Kaola-Delegator (no second outer start, no `codex-kaola-issue-77`). render --check PASS; test-issue-72 16/16; test-issue-74 65 assertions.

## item
Run a real ZCode app-server A→B continuation closed loop on a newly created isolation project/session only: A starts and hands off, B continues the same live Host from the project pointer, then exact-stop and `start --resume` the attested native sess_* and confirm old context; record original input, receipts, model replies, leftovers; on failure report honestly and correct the contract; re-run render/check/validate and freeze a new SHA; no fake pass, no finalize/push
status: done
dispatched: self; isolation project `/Volumes/WorkspaceA/ylminiserver/workspace/kaola-i74-iso-ab`; session `zcode-ISO74-orchestrator-ab`; receipts in `kaola-workflow/issue-74/evidence/live/`
result: Measured, not a full closed-loop PASS. Candidate `fdfa3cf4ecffe1aa492cbf25fe191f0622ff46e3` on `workflow/issue-74` (rebased onto main `0dacb07`, includes #67/#70/#72 archives). B live-attached the same Host from `.kaola/delegator-host.json` (`10-B-live-status.json`). Native id `sess_2499f37a-…` was real. First prompt refused `Select a model before continuing` (ZCode.app 3.12.3 rejects `runtimeModel`, empty Provider Registry). Exact stop spent the native id: `--resume` returned Session not found (`13-host-resume.json`). Contract updated: spent/unknown `sess_*` is cannot-resume. Fake is not a pass. `render --check` PASS. No finalize/push.

## item
Bounded root-cause on the owned isolation repo only: session/list the native sess_* before and after the first prompt, and before and after backend close/stop, to distinguish never-persisted vs close-deleted; one currently installed adapter-matched ZCode runtime; no second production Host; if a minimal fix can prove live and stopped-Host continuation freeze a new SHA, else keep cannot-resume, refresh delivery.md stale product names, and name the non-acceptable items
status: done
dispatched: self; isolation `/Volumes/WorkspaceA/ylminiserver/workspace/kaola-i74-iso-ab`; evidence `kaola-workflow/issue-74/evidence/live/probe-list/`
result: close-deleted. `sess_906aa4d5-…` listed after create and after send; `session/list` empty after `session/close` in the same process and in a fresh app-server (`probe-list/00-summary.json`). Not never-persisted. Headless 3.12.3 still cannot complete a model turn. Honest cannot-resume after exact stop kept. delivery.md rewritten to Kaola-Delegator / current candidate `b8ea07a844ba58ce44ec7c17c9bad3b6c6a5b126`. No second production Host. No finalize.

## item
Minimal A/B on the owned isolation repo: ACP holder exact stop without forwarding destructive backend session/close — does session/list keep the same real sess_* and does start --resume succeed; exact stop must still reap processes and not leave a live turn; no production Host, no global settings; land the adapter fix with real receipts and tests if it works, else report this item cannot be met
status: done
dispatched: self; isolation `/Volumes/WorkspaceA/ylminiserver/workspace/kaola-i74-iso-ab`; evidence `kaola-workflow/issue-74/evidence/live/probe-stop-resume/`
result: CANNOT MEET. Leg A close then resume: Session not found. Leg B kill app-server without close then resume: also Session not found and unlistable (`probe-stop-resume/00-summary.json` verdict `process-exit-and-close-both-unresumable`). Exact stop must reap the child, so skip-close is not a resume path. No adapter change. First model reply still a separate 3.12.3 limit. Candidate `d316c5093d54c3c54a5cc0ca393cc2c9db648bab`. No finalize.

## item
Bounded isolation check of the currently installed desktop zcode-cli SEA binary (Issue #69): locate it, see whether it supports adapter `app-server --stdio` or an equivalent entry, and run one isolation-only test of provider registry, first model reply, and exact-stop then sess_* resume; no global settings, no other sessions; land a minimal adapter plus freeze SHA if it works, else record the exact command/error as a local UAT hard block
status: done
dispatched: self; isolation `/Volumes/WorkspaceA/ylminiserver/workspace/kaola-i74-iso-ab`; evidence `kaola-workflow/issue-74/evidence/live/probe-sea/`
result: HARD BLOCK. `zcode doctor`: sea=no, default artifact=node-bundle. No standalone zcode-cli SEA Mach-O; desktop title zcode-cli is ZCode Helper. Equivalent `ELECTRON_RUN_AS_NODE=1 ZCode glm/zcode.cjs app-server --stdio` exits 1: missing `glm/provider/zcode-builtin.json` (`probe-sea/03-appserver.err`). Provider/model/resume tests not reached. No adapter change. No fake PASS. No finalize.

## item
Align workflow/issue-74 onto current main, drop the required `.kaola/delegator-host.json` pointer, recover a live Host from canonical repo plus standard Runner session name and existing status/receipts, adopt a precisely recorded nonstandard live Host, and on confirmed stop try sess_* resume or start a new standard Host from project state plus latest authorization — no second Host on ambiguity, no new registry
status: done
dispatched: self; templates/kaola-delegator/, README.md, AGENTS.md, tests/contract/test-issue-74-kaola-delegator.py, generated skills/
result: PASS at `431c0128a6474ca0035a53ebc65c142b73e4dcf5` on `workflow/issue-74`, rebased onto origin/main `f6be8a3` (0 behind, 9 ahead). No `.kaola/delegator-host.json`. Live recover is canonical repo + standard Host name + Runner `status`/receipts; unique nonstandard live name adopted; ambiguous location does not start. Confirmed stop may `--resume` attested `sess_*`; else a new standard Host is a new ACP session after authorization is complete (5730908734: no blank Host). `render --check` PASS (external 3111 B, handoff 6440 B, dispatch 8174 B). issue-74 tests 71 assertions. `validate.sh` PASS. Fake is not live ZCode proof. No finalize.

## item
Outer review of 431c0128: drop the unproven #74 ZCode adapter runtimeModel/create fallback and apply_coding_plan_model (generated copy too); add isolated receipts for post-stop new standard Host identity change; keep missing-auth non-start as documentation contract without impersonating the outer Agent
status: done
dispatched: self; scripts/kaola-zcode-acp.py restored from origin/main then renderer copy; tests/contract/test-issue-74-kaola-delegator.py; templates/kaola-delegator/; README.md; CHANGELOG.md
result: PASS at `0b49e6a8d70d6360bfcd659e33c819d1ffd69728`. Adapter + generated copy match origin/main (no apply_coding_plan_model). issue-74 tests 91 assertions including post-stop new Host holder change (`evidence/post-stop-new-host/`). Missing-auth non-start documented untested (`27-missing-auth-untested.json`). `test-zcode-acp-contract.py` 34/34. Full validate.sh not re-run (#78 load). No finalize.

## item
Run full ./scripts/validate.sh on freeze 0b49e6a in the issue-74 worktree after #78 validate is idle; keep original exit and failure lines; do not change the #79 adapter; do not finalize
status: done
dispatched: self; output lands in kaola-workflow/issue-74/evidence/validate-0b49e6a/
result: validate.sh exit=1 twice on freeze `0b49e6a8d70d6360bfcd659e33c819d1ffd69728`. Failed item `test-issue-49-grok-bot-host.py` (TemporaryDirectory __exit__ OSError errno 66 on repo/.git). Same single method fails on origin/main; not a #74 regression; no product/#79/#49 fix. Git clean; render --check PASS; adapter vs main empty; issue-74 suite 91/91 standalone. Missing-auth non-start remains documentation-only. No finalize.

## item
Restore Grok Bot per-Host-op co-location: before status/start/resume/send/stop on the bound target, attest with the existing locator `--project --worker zcode --session <exact HOST>` and refuse `refused`; Codex/generic do not use the locator; bridge stays thin
status: done
dispatched: self; templates/kaola-delegator/, templates/grok-bot/bridge.md.tmpl, README.md, tests/contract/test-issue-74-kaola-delegator.py, generated skills/ and hosts/grok-bot/
result: PASS at `8b6c20f2f30a6626d62b52536ae238d83b56accb`. Grok Bot bridge-only co-location in Skill/handoff; thin bridge pointer (2536 B). Codex/generic skip locator. issue-74 108 assertions; render --check PASS; grok-bot-verify PASS; Issue49SingleBridge/NotAnEighthPlatform/OrchestratorSemantics 16/16. Full validate not re-claimed green (#49 Errno 66 baseline stands). No adapter/#79 change. No finalize.

## item
Safely rebase workflow/issue-74 candidate `8b6c20f` onto current origin/main that contains published #79 ZCode 3.12.3 ACP compatibility (`b40813f` and any already-sunk follow-on archive), preserving Kaola-Delegator and the #79 adapter; repeat renderer/contract validation; do not touch other runs
status: done
dispatched: self; rebase in `.kw/worktrees/issue-74` onto origin/main `c806240` (contains `b40813f`); then onto sunk #80 `c963bad`; validation receipts in `kaola-workflow/issue-74/evidence/validate-02f37b0/`
result: PASS. Rebased 11 #74 commits onto origin/main with #79 adapter kept byte-identical (`cb029a22…`). Conflicts: CHANGELOG, validate.sh suites (kept both 74 and 79), adapter hunks from the old fallback (took #79). #80 git-maintenance knobs kept in test-issue-49. `render --check` PASS; grok-bot-verify PASS; issue-74 108; issue-79 19/19; zcode-acp 34/34. issue-49 append probe overflowed 2536/2560 bridge; equal-length probe committed as `44a17b9`; rerun 43/43, no Errno 66. Other runs untouched.

## item
Prove the previously missing real A→B path in a new isolated scratch Git repo using the real installed ZCode ACP adapter from the integrated candidate: A starts or finds exactly one standard Host with explicit current test authorization, Host loads Project Runner, dispatches one tiny authorized Devin SWE-2 Max worker, ends turn, event wake reports worker result, B attaches the same live Host and follows up, then exact stop/cleanup; no global install, no credential copy, no existing live Hosts; distinguish authentic ZCode model/Runner events from fake tests and untested legs; if the environment cannot prove it, record the precise blocker, not PASS
status: done
dispatched: self; isolated scratch Git repo under /tmp/kpr-i74-ab-*; Host `zcode-I74AB-orchestrator-main`; candidate adapter from `.kw/worktrees/issue-74` HEAD; receipts in `kaola-workflow/issue-74/evidence/live-ab-44a17b9/`; do not touch existing live Hosts
result: PASS (authentic ZCode 3.12.3, not fake). Scratch `/tmp/kpr-i74-ab-KNdEO4/repo`. A `status` no-session then `start` `state=ready` mode yolo applied, adapter 0.3.3 matching main. Host loaded Project Runner, dispatched `devin-I74AB-i74-receipt` swe-2-max, end_turn 43032 ms. Worker wrote `RECEIPT.txt`=`KAOLA74-AB-TOKEN`. Host `wait` received worker idle event, quoted token, stopped that worker. B attached same holder `7efadb01…` and `acp_session_id=zcode-1` with no start; follow-up quoted token. Exact Host stop `residual_pids=[]`. Foreign sessions unchanged. No pointer file, no global install, no credential copy. Untested: Grok Bot UAT, `--resume sess_*`, missing-auth non-start. See `evidence/live-ab-44a17b9/RESULTS.md`.

## item
When #80 has sunk, rebase again at that safe boundary, freeze SHA and raw evidence for independent outer review; no finalize/archive/sink/merge/push before outer ACCEPT
status: done
dispatched: self; #80 closed and sunk at origin/main `c963bad`; rebase workflow/issue-74 again in `.kw/worktrees/issue-74`; freeze SHA + evidence after renderer/contract validation and A→B attempt
result: PASS freeze `44a17b97e5d9fee90352efd00d74b72832f1e5c9` (0 behind / 12 ahead origin/main). #80 knobs present. Evidence `kaola-workflow/issue-74/evidence/live-ab-44a17b9/` and `validate-02f37b0/`. delivery.md and `evidence/shas.txt` updated. No finalize/archive/sink/merge/push. Waiting outer ACCEPT.

## item
Close the outer-review gap: after the first Host beat, Kaola-Delegator must verify Project Runner load, authorized role, and heartbeat/worker identity from plan/authorization plus Host file-read/work-product evidence and the first dispatch receipt — not Host self-description; mismatch is corrected, not accepted as complete; no new script, gate, ledger, or budget; renderer generate; render --check and focused tests; freeze a new SHA; do not re-run live A→B; no finalize
status: done
dispatched: self; templates/kaola-delegator/references/handoff.md.tmpl, templates/kaola-delegator/SKILL.md.tmpl, tests/contract/test-issue-74-kaola-delegator.py, generated skills/; freeze SHA on workflow/issue-74
result: PASS freeze `942c4c8b6332533e106835b603f6ab823ebb78f5`. Handoff gained "After the first Host beat"; Skill has a short pointer. No new script/gate/ledger; budgets unchanged (Skill 3667/4096, handoff 8007/8192). `render --check` PASS; grok-bot-verify PASS; issue-74 124 assertions PASS; progressive-disclosure 21/21. Live A→B not re-run. No finalize/merge/push.

## item
Wait until GitHub issue #83 is remotely CLOSED and origin/main has sunk it at a safe idle point (no MERGE_HEAD, exclusive sink released); do not mutate main or the #83 run
status: done
dispatched: self; monitor gh issue 83 + origin/main; do not touch `.kw/worktrees/issue-83` or main
result: PASS. #83 remotely CLOSED at 2026-09-18T17:39:13Z. origin/main `94d6792c297e725e3f46d7e820f01a48728f2fa8` includes the #83 sink archive. No MERGE_HEAD. Exclusive sink released.

## item
Rebase workflow/issue-74 freeze `942c4c8` onto that new origin/main, preserving Kaola-Delegator and both sides' validate suites/docs; re-run render --check and full validate.sh; freeze the new SHA, diff, and validation evidence for outer confirmation; do not re-run live A→B; do not finalize/sink/push; protect other sessions
status: done
dispatched: self; rebase in `.kw/worktrees/issue-74` onto origin/main `94d6792`; evidence in `kaola-workflow/issue-74/evidence/validate-rebase-94d6792/`
result: PASS freeze `337f805add1a773ea14a91078aed9be8c48dd3de` (0 behind / 13 ahead origin/main `94d6792`). validate.sh keeps #83 SKIPPED/run-all lanes plus #74 and #83 suites. `render --check` PASS; grok-bot-verify PASS; `git diff --check` PASS; full `validate.sh` exit 0 (issue-74 124 assertions, issue-83 3/3). Evidence `kaola-workflow/issue-74/evidence/validate-rebase-94d6792/`. Live A→B not re-run. No finalize/sink/push. Waiting outer confirmation of this SHA.

## item
On the released main after #83 CLOSED (origin/main at `94d6792` plus any already-landed archive-only follow-on), confirm workflow/issue-74 is rebased there without editing #83 archive files or other runs; re-run render --check, full validate.sh, and grok-bot-verify; freeze SHA/diff/evidence for outer confirmation; no finalize/sink/push
status: done
dispatched: self; worktree `.kw/worktrees/issue-74`; evidence `kaola-workflow/issue-74/evidence/validate-rebase-88042cd/`; do not edit `kaola-workflow/archive/issue-83`
result: PASS freeze `337f805add1a773ea14a91078aed9be8c48dd3de`. Already 0 behind / 13 ahead origin/main `88042cd` (includes sink `94d6792`). Did not rebase-drop the archive commit and did not edit `kaola-workflow/archive/issue-83`. Both suites kept. This-round `render --check` PASS; grok-bot-verify PASS; `git diff --check` PASS; full `validate.sh` exit 0 (124 issue-74 assertions). Evidence `validate-rebase-88042cd/`. No finalize/sink/push.

## item
Outer review of `337f805` is not ACCEPT: in the issue-74 worktree only, (1) Host stop/live attach must use receipt `holder_instance_id` via `--expected-holder-instance-id`; (2) name the fake two-layer test honestly and cite live A→B evidence; (3) new-Host fixture must not start before authorization, and missing-auth non-start must be real or explicitly untested; (4) filtered reinstall/uninstall must not leave a stale Delegator. Keep live A→B evidence and #83 semantics; renderer generate; no budget raise; rebase onto main after #82 sink; focused plus full validate; freeze SHA; no finalize
status: done
dispatched: self; rebase onto origin/main after #82 CLOSED; edits in templates/kaola-delegator, install-local.sh, tests/contract/test-issue-74-kaola-delegator.py, test-installer-runtimes.sh; evidence under kaola-workflow/issue-74/evidence/
result: PASS freeze `4c76a1533a24bcceccdd5484303d98c519b7f8bc` on origin/main `513e8e1` (#82+#69+#83). Four review items landed. `render --check` PASS; grok-bot-verify PASS; `git diff --check` PASS; full `validate.sh` exit 0 (140 issue-74 assertions; installer runtimes PASS). Evidence `validate-holder-fix/`. Live A→B not re-run. No finalize/sink/push.

## item
Targeted corrections on freeze `4c76a15` (not ACCEPT): (1) handoff resume after exact stop is capability-dependent — try attested native `--resume` first, new Host only after proven failure and complete authorization; do not claim sess_* always disappears and do not treat #84 as merged; (2) fixture ORIGINAL_TASK uses an explicit bounded token quota and delivery/stop boundary, not quota_token=unspecified while calling authorization complete; (3) restore Afterward warning that the outer Agent is not automatically awakened by inner Host activity. Re-render, focused plus full validate, freeze SHA. Do not touch #81/#84 or finalize
status: done
dispatched: self; templates/kaola-delegator/references/handoff.md.tmpl, tests/contract/test-issue-74-kaola-delegator.py, generated skills/; evidence kaola-workflow/issue-74/evidence/validate-resume-wording/
result: PASS freeze `536c6bd19c309bcf51d0224a1206926fd7b18639`. Handoff tries attested `--resume` first; native id is backend-dependent. Fixture quota_token=1-short-task plus delivery_stop_boundary. Afterward restores outer-Agent not auto-awakened. `render --check` PASS; grok-bot-verify PASS; `git diff --check` PASS; full `validate.sh` exit 0 (148 issue-74 assertions). No #81/#84 adapter edits. No finalize/sink/push.

## item
Make ORIGINAL_TASK quota_account and quota_token unambiguous figures (not an account name and not a task count) so calling it complete authorization before start matches Issue #74's separated quota units; update assertions; focused plus full validate; freeze SHA; no finalize
status: done
dispatched: self; tests/contract/test-issue-74-kaola-delegator.py only; evidence kaola-workflow/issue-74/evidence/validate-quota-figures/
result: PASS freeze `eb9585208d40da0c9f21add3596278833b0ba3bb`. ORIGINAL_TASK is quota_account=1 job and quota_token=10000 tokens. `render --check` PASS; grok-bot-verify PASS; `git diff --check` PASS; focused 151 assertions; full `validate.sh` exit 0. No production policy/schema. No finalize/sink/close/release.


