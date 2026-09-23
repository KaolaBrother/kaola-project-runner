# Issue #126 live evidence — Codex Host entry `$kaola-project-runner`

Method of #119 (`kaola-workflow/archive/issue-119/evidence/`), 2026-09-23, this Mac.

## Environment

- Shadow `HOME=/tmp/kpr126-home`. Its Skill roots were populated only by
  `HOME=/tmp/kpr126-home ./scripts/install-local.sh --runtime codex --method copy`
  from the run worktree, so `~/.codex/skills` there holds this build only (no `~/.agents/skills`).
  `~/.codex/auth.json` is a symlink to the real account file. No real `config.toml`,
  `AGENTS.md` or other Skills were copied in.
- `KAOLA_ACP_RECORD_ROOT=/tmp/kpr126-records` (isolated, so the sweep touches only this run).
- Wrapper `m0-trigger/kpr126-run.sh`: unsets every inherited `KAOLA_*`/`KPR_*` (this session
  runs under a ZCode Host) and `CODEX_HOME`, sets `npm_config_cache` to the real npm cache (so
  npx does not re-download the pinned codex-acp), then execs the worktree `scripts/kaola-tmux.sh`.
- codex-acp 1.13.0 (`@openai/codex@0.155.1` pin), default tier gpt-6-sol / effort high.

## Steps and builds

| Step | Build in the shadow roots | Evidence |
|---|---|---|
| M0 A discovery / C entry / N negative control | e4f477b (main, entry empty; standalone starts are not Host starts) | `m0-trigger/{A,C,N}-codex.json`, driver `probe.py`, `run-m0.sh` |
| M0 attempt 1 (three parallel cold npx starts) | e4f477b | `m0-trigger/attempt1-parallel-init-timeout/` — all `acp-initialize-timeout` before any turn; the sequential rerun is the result |
| D3 steps 1–6 (codex Host + codex worker) | 2394d57 (entry filled) | `d3/` — `summary.json`, receipts `1-`,`2-`,`5-`,`6-*.json`, `host-events.jsonl`, `analysis.json` (`analyze.py`), `uat.json` + `carrier-rebuilt.txt` (`uat.py`) |
| Sweep | — | `d3/sweep-positive-control.json`, `d3/sweep-final.json`, `d3/ps-after-sweep.txt` |

Main Skill `SKILL.md` is byte-identical in e4f477b, 2394d57 and the final candidate
(sha256 918d80e40f89…); the candidate after 2394d57 changes only tests, docs, and the
`host-entry-matrix.md` reference (plus the derived `main-skill-build.json` hashes).

## Results

- A: `available_commands` and the reply list `$kaola-project-runner` (`$` prefix).
- C: prompt line 1 `$kaola-project-runner`; no tool call; reply is verbatim the third sentence
  under "Hosts" (added afeb43b, 2026-09-22): **E2**.
- N: same question without the entry line, no tool call: `SKILL-NOT-LOADED`.
- D3: Host start ready (default tier). Step 2 (handoff opened by `$kaola-project-runner`) quoted
  the second paragraph under "Two entry points" (#119-only text), **E2**, with no Skill read or
  grep. The worker started by the Host reported `heartbeat_host_source: dispatcher`, bound to
  `codex/codex-KPR-orchestrator-d3`. Carrier delivered at 251 and 459, confirmed at 458 and 530.
  The fingerprint equals the rebuild, whose lines 1–2 are `$kaola-project-runner` /
  `kaola-host-notify/1: event-driven heartbeat carrier (Codex CLI Host)`. Step 5 (carrier-woken
  beat) quoted the first sentence under "Heartbeat", **E2**, with no read. In that beat the Host
  read the worker (`DEEP-WORKER-OK`), exact-stopped it (`stopped: true`, `residual_pids: []`) and
  rewrote `.kaola/heartbeat-prompt.json`. Host stop `residual_pids: []`.
- Sweep: the positive control matched and stopped holder 66863; the final sweep found
  `matched_pids: []`, `residual_pids: []`, rc 0; no process argv contains `kpr126`.
- Worker choice: under the shadow `HOME` a dsh worker had no provider credential
  (`no API key for provider route "deepseek-official"`) and claude-code answered
  `Not logged in`, so the D3 worker is codex (#119's dsh row likewise used another worker).
