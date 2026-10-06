# Issue 264 mission6 core lane — delivery-r3 (fixed-candidate verification)

Lane: `core` under `/tmp/kpr-i264-host-chain-1035/core/` (same assignment, same holder/session
authority; Workflow OFF; writes only beneath this lane). Continuation of delivery-r1/r2.
No repository, installed Skill, global config, account, or consumer-project writes.

## Candidate under test

- Frozen Host-committed repair: **`9f7789812424b484e1e26a529a7b212f1ea6bd4a`** in
  `/Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-264` (HEAD verified).
- Exported read-only copy used by all runs: `core/src-r3` (`git archive HEAD` export;
  holder/dispatch/acp files diff-identical to worktree; no mutation during measured runs).
- Fix content verified in copy:
  - `src-r3/scripts/kaola-acp-holder.py:1151` — `NATIVE_COMPACT_RECOVERY_PLATFORMS = frozenset()`
    (Codex ACP no longer skips the bounded reload as native-owned).
  - `src-r3/scripts/kaola-acp-holder.py:3740` — recovery-entry clause: input/checked/unavailable/
    optional applied only, **"never retained"**, non-overlapping scopes; ordinary `retained`
    guidance now scoped to business inputs.
- Actually-used src-r3 hashes (sha256):
  - `scripts/kaola-acp-holder.py` `8158497743f852152d89e747c15bf803e59f2d11e8edec795bfffd601a9d6ae5`
  - `scripts/kaola-dispatch.py`    `f80610b2a8a4ea57ba61d1144d7c531651c0f92b4c9db65c66d6893b5d7c566d`
  - `scripts/kaola-acp.py`         `299ec8d005d380bd0a29a7aeba70eb73a948301948b80a88b44268068b831e73`
  - `scripts/kaola-opencode-acp.py` `47a3b97d22b86a76457260f18030664a172ee353d97246804ee59292cde1ec67` (unchanged)
  - `scripts/kaola-codex-compact-hook.py` `c21e463e5b2bc69609347b220124197c4719b3607525e5a518b3e13318462682` (unchanged)
  - `scripts/kaola-tmux.sh`        `b03d9fca3ded8f98bad7788c175f76da2815ca85aeeb9ebd25d7721283be5b8b` (unchanged)
- Driver: `core/bin/drive_lane.py` (KPR_LANE_SRC=src-r3, per-lane KPR_LANE_DIR). Fixture AGENTS.md
  is the NORMAL seeded controller fixture (no recovery-entry supplement — r2's labeled
  controller-assisted note was NOT carried into r3). No schema/validator change; no replay,
  no manual node start, no fake business write.

## Results on fixed candidate 9f778981 (2026-10-06 local)

| Runtime / run | O1 real completed signal | O2 auto KPR reload: delivered + full installed-Skill reread + bounded continuation | O3 duty→auto node→checkpoint→exact reclaim | Verdict |
|---|---|---|---|---|
| Codex `codex-r3` | VERIFIED — `compaction_update` `status:"completed"` @97, occurrence `01a1110a-f459-7572-ae74-fd27630fc565`, session/role bound | VERIFIED — `compact_reload_delivered` @100 (fp `d862ba9d…`); raw read payloads `.agents/skills/kaola-project-runner/SKILL.md` @129 (17407B) + `codex-kaola-project-runner/SKILL.md` @134 (10298B) + refs @139/141/240; `turn_ended` end_turn @400; TASK-B progress.md entry | VERIFIED — duty @102 → node `15bc0faf…` @401 → batch `b-9b614a237e56` @402 → `recovery#1` settled **verified** @403 → stopped @408 → host exit 0 @409 | **VERIFIED (candidate)** |
| Grok CLI `grok-r3` | VERIFIED — `_x.ai/session_notification` auto-compact completed @153, session `01a11110-…` | VERIFIED — `compact_reload_delivered` @161 (fp `bf48d26d…`); native `read_file` payloads `.grok/skills/kaola-project-runner/SKILL.md` @263 (17407B) + `grok-kaola-project-runner/SKILL.md` @267 (10193B), 21 read events; turn_completed end_turn; TASK-B progress.md entry | VERIFIED — duty @163 → node `69e648ed…` @554 → batch `b-bb40068a7a55` @555 → `recovery#1` settled **verified** @564 → stopped @569 → host exit @571 | **VERIFIED (candidate)** |
| OpenCode `opencode-r3` | VERIFIED — `opencode/compaction` completed @35, occurrence `msg_111141a56001x4OgkGnxQyOBSf`, session `ses_eeeeed1c…` | VERIFIED — `compact_reload_delivered` @37 (fp `bf48d26d…`); `<skill_content>` payloads @58+ (runner 17407B + opencode skill 10597B, sha256s quoted in TASK-B), 18 read events; turn_completed; TASK-B progress.md entry | PARTIAL — duty @38 → node `0ad589eb…` @236 → batch `b-b0d493bc52ae` @237 → `recovery#1` **settled** (schema-clean) BUT sibling entry `qa-observe` rejected `not-in-batch` → checkpoint `partial` @238 → `maintenance_failure_recorded` @241 → stopped @245 → host exit 0 @264 | **PARTIAL (see below)** |

## Codex r3 detail (the ACP full chain, now delivered not native-owned)

- Host holder `9a2739a31e224035fd808aabf761c955`, session `01a11107-6cc7-7dc2-a38c-7fba388a9738`.
- Versions/selection: codex child **0.160.1** (requested 0.160.0), adapter `@agentclientprotocol/codex-acp` **2.0.1**
  (adapter hash `2729d2a39c9fde47c494828a76c7eb2fabc0f9940f2723183426c1afbf1a5e7d`; child binary
  `/Users/ylmacstudio/.local/bin/codex` `61b0194f3bb6534439c8d26a3ed57d0805f84b884588b761795323eeb92fcf70`).
  Applied: model `gpt-6.1-sol`, `reasoning_effort=high`, `fast=off`, `mode=agent-full-access`;
  `session.compaction` negotiated (capability `{}` sent, accepted).
- Node1 (business) holder `e9680a941a6cfbb74935d5e792b31f9d`, batch `b-f2b80f3f5610`: settled
  verified @87, stopped @92.
- `/compact` → real compaction (`compact_turn` turn_completed; usage 21843→6100 of 258400).
- Cursor 97 `compact_reload_detected` (`acp-compaction-update`, occurrence `01a1110a-f459…`).
- Cursor 100 `compact_reload_delivered` — **the fix path**, not `compact_reload_native_owned`.
- Delivered turn (fingerprint `d862ba9d…`, `turn_ended` @400, `stop_reason: end_turn`):
  raw `kind:"read"` payloads `/Users/ylmacstudio/.agents/skills/kaola-project-runner/SKILL.md` @129,
  `/Users/ylmacstudio/.agents/skills/codex-kaola-project-runner/SKILL.md` @134, plus `cat` of
  `references/duty-reconcile.md`/`sideagent-node.md` @139, `wc -c`/`tail` verification @141,
  `references/lifecycle-state.md` @240 — actual tool payloads in stream, not summaries.
  `.agents/skills` is a real installed location (generic install root; main SKILL.md identical
  17407B to the codex-dir copy).
- Cursor 102 `host_compact_maintenance_registered` `recovery#1`, `signal_cursor:97`,
  `evidence → events.jsonl#97`.
- Safe boundary honored: `turn_ended` @400 precedes `sideagent_node_started` @401.
- Node2 emitted (raw `--entries`, node record cursor 961):
  `[{"input":"host:tasks/qa-observe@4","retained":"tasks/qa-observe"},
    {"input":"recovery#1","checked":{"authorization":[7 srcs],"duties":[4 srcs],"links":[5 srcs]}}]`
  — `retained` correctly only on the business entry; `recovery#1` has `input`+`checked` only.
- `sideagent_node_settled` @403 `checkpoint:"verified"` (settled `[host:tasks/qa-observe@4,
  recovery#1]`); worker events confirmed; `sideagent_node_stopped` @408 `{stopped:true}`;
  `process_exited` code 0 @409; `residuals: []`; host_stop `agent_exit_code 0`, `residual_pids []`.
- `hook_bind` still ran (`result:"ok"`, project `.codex/hooks.json` + binding written) — but per the
  r2 probe, hooks are never dispatched on the App-Server route; the delivered reload is what ran.
  No hooks needed for this verified chain.

## Grok r3 detail (checkpoint counterpart)

- Host holder `fe9c62d512e38f7afc68e8e2a7a6b3a4`, session `01a11110-e5a5-76d0-8d39-c31af9bfde21`.
- Binary `/Users/ylmacstudio/.grok/downloads/grok-1.0.46-macos-aarch64`
  (`e8daa302364c9c3b6a5546d511cfbd1ab5e5d407a9b04282f660665ea405f9f3`); skill meta 1.0.40.
  Applied: `grok-4.7`, `reasoning_effort=xhigh`; fast n/a.
- Node1 `684f56f045fa00541c7bb20d135261fd` batch `b-d7c4f7cf9162`: verified @143, stopped @148.
- Signal @153 (Grok `_x.ai/session_notification` auto-compact; occurrence_id null — Grok form),
  delivered @161, duty @163.
- Node2 `69e648ed94f573307902351d6fc06269` batch `b-bb40068a7a55` (recovery-only batch): emitted
  single entry `{"input":"recovery#1","checked":{"authorization":[4],"duties":[5],"links":[6]}}`
  incl. `events.jsonl#153` signal ref — no `retained`, no `unavailable` needed.
- `settled: ["recovery#1"]`, `verified:true` @564; stopped @569; exit @571; `residuals: []`.

## OpenCode r3 detail (truthful PARTIAL — different failure than r1)

- Host holder `787fbe5f79d5ea50cb4133903ed2498d`, session `ses_eeeeed1c6ffecvdcxvYt8yv9tG`.
- Binary `e7bef8c3…`; adapter `kaola-opencode-acp.py` `47a3b97d…` (unchanged); applied model
  `opencode-go/deepseek-v4.1-flash`.
- Node1 `18c86e5f…` batch `b-ba0673b56ae3`: verified @27, stopped @32.
- Signal @35 `opencode/compaction` completed (`msg_111141a5…`), delivered @37, duty @38.
- Node2 `0ad589eb80abb75aa92ab696ad84d261` batch `b-b0d493bc52ae` (recovery-only batch): emitted
  `[{"input":"qa-observe","retained":"tasks/qa-observe"},
    {"input":"recovery#1","checked":{3 scopes},"unavailable":{}}]`.
- Result: `recovery#1` **did settle** (in `settled`, schema-valid — the r1 `retained` defect did NOT
  recur). Checkpoint verdict `partial` because the node's **extra unsolicited sibling entry**
  `{"input":"qa-observe",…}` was `not-in-batch` (`returned_to_host.qa-observe`), then
  `sideagent_maintenance_failure_recorded` @241 `reason:"checkpoint-partial"` — the designed
  degraded path, exercised for real. Stopped @245, host exit 0, `residuals: []`.
- Honest label: the fixed prompt's recovery-entry contract held (clean `recovery#1`, no `retained`,
  non-overlapping scopes). The remaining partial is a node-composition miss on an entry the batch
  never requested — not the repaired defect. Schema unchanged. Reported as-is, not relabeled.

## Cross-run observations

- The `retained`-on-`recovery#1` defect is eliminated in all three measured node emissions
  (codex `…@961`, grok `…@895`, opencode `…@1108` raw `--entries` inspected).
- Codex ACP now takes the normal delivered reload (`compact_reload_delivered`, not
  `native_owned`) — matching the r2 finding that App-Server `thread/compact/start` never
  dispatches hooks (TUI-only boundary stands; that probe evidence is unchanged and separate).
- All nodes remain Codex/luna maintenance nodes (`--session-role sideagent`, `tier:"luna"`) —
  correcting my earlier mislabeled "three models" diversity: host-model diversity ≠ node-model
  diversity (Host review, /tmp/kpr-1063-core-r2-host-review.md).
- Parallel `grok-r3`/`opencode-r3` node holders coexisted under the shared logical session name
  `codex-KPR1035C-sideagent` as separate spawned processes (distinct holder ids, sockets, record
  dirs, heartbeat hosts) — no attach/steal; distinguishable by `holder_instance_id`+batch.

## Provenance and cleanup

- `~/.codex/config.toml` (6959B, mtime 2026-10-06 19:57:55): r3 added three `[projects."…"]` trust
  entries — `core/codex-r3/run/repo` (L199), `core/grok-r3/run/repo` (L205),
  `core/opencode-r3/run/repo` (L208). Core-lane total now 7 entries (r1 codex/grok/opencode
  L178/184/187, r2 opencode L193, r3 ×3). No `hooks.state` entries for lane repos; only pre-existing
  global `~/.codex/hooks.json` session_start state (L211/214, not mine). No reversal — no preimage.
- Cause (unchanged candidate behavior, now precisely attributed): `platforms/codex.yaml`
  `acp_env_allowlist: "CODEX_API_KEY,OPENAI_API_KEY,CODEX_PATH"` — the launch broker filters
  child env to the manifest allowlist, so `CODEX_HOME` set on the driver never reaches
  holder-spawned codex processes (verified: `ps eww` shows CODEX_HOME on the driver, absent on the
  holder). Every codex process (hosts AND Codex/luna sideagent nodes) therefore resolves the real
  `~/.codex` and auto-persists per-repo trust. Source-custody item for Host: decide whether
  `CODEX_HOME` belongs in the codex manifest allowlist; no mutation made.
- Lane auth copy `codex2/codex-home/auth.json` (4249B, mode 0600, mtime 2026-10-06 18:56:47)
  removed after its processes were confirmed dead (probe daemons 56139/56168 exact-stopped in r2);
  contents never logged or published. Other lane/`KPR103ED2`/consumer processes untouched.
- r1 deleted Codex records remain unavailable — `/tmp/kpr-1056-core-original-capture.json` is
  provenance only, not reconstructed evidence (per r2 correction, carried forward).
- All three r3 drivers exited; `pgrep KPR1035C` empty; no lane tmux sessions; receipts:
  `core/{codex-r3,grok-r3,opencode-r3}/receipt.json` + `receipts/` + `run/records/**`.

## Verdict scope and limits

- These are **candidate** results for commit `9f778981` measured via the lane copy — not product
  verdicts; product integration/review/verdict belongs to Host.
- Codex full chain now verified end-to-end on the fixed candidate (signal → delivered reload →
  full installed reread → bounded continuation → duty → auto node → verified checkpoint →
  exact stop). Grok verified. OpenCode: chain ran; `recovery#1` settled; checkpoint-level partial
  from an out-of-batch sibling entry — truthful, not relabeled.
- All-runtime automatic activation remains UNVERIFIED: seven runtime rows (Claude Code, Cursor CLI,
  Devin, Droid, DSH, Kimi CLI, ZCode) are outside this lane's scope; no universal fault-freedom
  claim. This delivery updates evidence only for codex/grok/opencode on candidate `9f778981`.
- No self-finalize, no capability-matrix edit, no issue lifecycle action. Helper seat retained for
  Host judgment.
