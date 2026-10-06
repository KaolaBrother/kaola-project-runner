# Issue 264 mission6 core lane — delivery-r4 (candidate 24a2355a)

Lane: `core` under `/tmp/kpr-i264-host-chain-1035/core/` — same assignment/holder authority,
Workflow OFF, writes only beneath this lane. Continuation of r1/r2/r3. No repo, installed Skill,
global config, account, or consumer-project writes. r1–r3 evidence and negatives preserved.

## Candidate under test

- Frozen repair: **`24a2355a226fc371b6502ea6b254b2157da6efa6`** (worktree
  `.kw/worktrees/issue-264` HEAD verified), on top of `9f778981`.
- Read-only copy: `core/src-r4` (`git archive HEAD`; no mutation during measured run).
- Fix verified in copy:
  - `src-r4/scripts/kaola-launchd-broker.py:64-67` — `PASS_ALWAYS` now includes `CODEX_HOME`
    with comment explaining the non-Codex-Host→Codex-node boundary; no broad env forwarding.
  - `src-r4/scripts/kaola-acp-holder.py:3719-3720` — node prompt: "Checkpoint only this batch's
    selected input ids, verbatim. Task ids read as recovery sources are not extra inputs. With
    no selected business changes, emit no business entries."
  - `src-r4/templates/orchestrator/references/sideagent-node.md` + generated copy L76-79 — same
    verbatim-ids contract (both copies identical, `82e79574…`).
- src-r4 hashes (sha256): holder `f455cd271d20b2f15c36045b31f4fdf4d067615c0f4937b0eda2473a09a1aa56`,
  broker `c39e68944bb91a6f6dbfdff3f8c1c736b09beb03078a8dbe6220d515c3fe3a68`,
  dispatch `f80610b2a8a4ea57ba61d1144d7c531651c0f92b4c9db65c66d6893b5d7c566d` (unchanged),
  opencode adapter `47a3b97d22b86a76457260f18030664a172ee353d97246804ee59292cde1ec67` (unchanged).
- Driver: `bin/drive_lane.py`, `KPR_LANE_SRC=src-r4`, `KPR_LANE_DIR=opencode-r4`, plus
  `CODEX_HOME=/private/tmp/kpr-i264-host-chain-1035/core/opencode-r4/codex-home` exported in the
  driver env. Normal seeded fixture AGENTS.md — no recovery supplement (r2's labeled
  controller-assisted note stays labeled, not carried). No schema/transport change.

## One measured run: `opencode-r4` (2026-10-06 20:26–20:35 local)

All three outcomes on the fixed candidate — **VERIFIED** end to end:

| Stage | Evidence |
|---|---|
| O1 real completed signal | `compact_reload_detected` @36 — `opencode/compaction` completed, occurrence `msg_11130478f001ZiTmloR28am2gC`, session `ses_eeed1b309ffeckayL5LnNXQafu`, host holder `cc34c0f714aa05848b443fc10511c487`, role host |
| O2 delivered reload + installed reread + continuation | `compact_reload_delivered` @38 (fp `bf48d26d…`); 24 read events incl. raw `kind:"read"` of `~/.config/opencode/skills/kaola-project-runner/SKILL.md` @126 and `opencode-kaola-project-runner/SKILL.md` @125, output @127/128 = **complete numbered file bodies lines 1-166 / 1-264** (full file incl. YAML frontmatter — closes the r3 role-file completeness qualification); bounded `turn_ended` end_turn @693; TASK-B progress.md entry |
| O3 duty→auto node→VERIFIED checkpoint→exact reclaim | `host_compact_maintenance_registered` `recovery#1` @39 (`evidence → events.jsonl#36`); node `3621523a78d499b840e006408dd0ce6e` auto-started @694 after turn end (safe boundary); recovery-only batch `b-dc2215b9f4e2` @695; node emitted **single-entry** `[{"input":"recovery#1","checked":{3 scopes},"unavailable":{}}]` (node record call @860 — `qa-observe` appears only inside checked source refs, no extra input); `sideagent_node_settled` @696 `checkpoint:"verified"`, `settled:["recovery#1"]`, `returned:{}`; `sideagent_node_stopped` @701 `{stopped:true}`; `process_exited` 0 @702; `residuals:[]`; `host_stop.agent_exit_code:0` |

Node1 (business) beforehand: holder `dc615f8c8d23a4e0263a6455f8476041`, batch `b-c5d4e94fe7a0`,
settled verified @28, stopped @33.

Runtime/adapter bindings: OpenCode binary `e7bef8c3…`, adapter `kaola-opencode-acp.py`
`47a3b97d…` (unchanged), applied model `opencode-go/deepseek-v4.1-flash`. Codex node: child
0.160.1, adapter codex-acp 2.0.1 `2729d2a3…`, tier `luna`.

## CODEX_HOME isolation — measured on the live run

Driver exported `CODEX_HOME=/private/tmp/kpr-i264-host-chain-1035/core/opencode-r4/codex-home`
(private lane home; `auth.json` copied once, 0600 — same already-authorized account, no
login/switch, never logged).

Selected-key `ps eww` readback during the run (path only, no full env/secrets):

- Host holder pid 7216 (opencode): broker-preserved env.
- Node1 codex holder pid 9657 (`dc615f8c…`): `CODEX_HOME=/private/tmp/…/opencode-r4/codex-home` ✓
- Node1 native `npm exec codex-acp` pid 9680: same `CODEX_HOME` ✓
- Node2 codex holder pid 73610 (`3621523a…`): same ✓
- Node2 native `npm exec codex-acp` pid 73636: same ✓

Application evidence inside lane home (created by codex itself): `installation_id`,
`cache/`, `goals_1.sqlite*`, `state_5.sqlite*`, `thread_history_1.sqlite*`, `queue_1.sqlite*`,
`memories_1.sqlite`, `sessions/`, `skills/`, `plugins/`, `shell_snapshots/`, `tmp/`,
`models_cache.json` — a complete private runtime tree.

Global `~/.codex/config.toml` before/after selected-key compare:

- before: 6959B, mtime 19:57:55, 42 `projects.*` keys, 0 `opencode-r4`
- after:  **6959B, mtime 19:57:55, 42 keys, 0 `opencode-r4`** — byte-identical, zero global writes
- lane home: **no `config.toml` was created at all** — no trust persistence fired inside the lane
  either; the earlier global `[projects]` additions came from the pre-fix path where CODEX_HOME
  was dropped. The measured difference is now exact: global untouched, runtime state confined.

The optional direct-Codex env probe was NOT needed: the opencode run already resolved the full
propagation chain (driver → outside OpenCode Host holder → auto-spawned Codex/luna node → native
codex-acp child), which is the seam the fix targets.

## Cleanup / provenance

- All lane processes exited by receipt (`residuals:[]`, host exit 0); `pgrep KPR1035C` empty;
  monitor shells reaped; foreign holders (`KPR103ED2`, consumer vrpcadcore/vrpai, repo hosts)
  untouched.
- Lane credential copy `opencode-r4/codex-home/auth.json` (4249B, mode 0600, created 20:26:39)
  removed after all owned processes confirmed dead; contents never surfaced.
- Global `~/.codex/config.toml` retains the seven earlier core-lane trust keys (r1×3, r2×1, r3×3)
  with unknown preimage — NOT reversed, per instruction; r4 added none.
- No installation, login/account/model switch, schema weakening, manual node start, fake business
  write, fixture supplement, or replayed writes. The six unchanged-baseline lifecycle QA
  discrepancies remain as reported by Host; no whole-suite claim.

## Verdict scope

- Candidate `24a2355a` measured via lane copy — product verdict/integration is Host custody.
- Core lane state: codex VERIFIED (r3), grok VERIFIED (r3), opencode VERIFIED (r4, with
  `recovery#1`-only batch and verbatim input ids); CODEX_HOME isolation verified live on the
  opencode path. r3's opencode `partial` is preserved as negative history, not relabeled.
- All-runtime automatic activation remains UNVERIFIED: seven rows (Claude Code, Cursor CLI, Devin,
  Droid, DSH, Kimi CLI, ZCode) are outside this lane. No universal fault-freedom claim; no
  publication or lifecycle action by this lane. Helper seat retained for Host judgment.
