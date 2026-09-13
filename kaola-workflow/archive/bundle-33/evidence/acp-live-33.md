# Issue #33 live ACP evidence — 2026-09-13

Candidate: worktree `.kw/worktrees/bundle-33` (branch `workflow/bundle-33`), real
`devin acp` agent (CLI 3000.10.21, affogato 0.0.0-dev). Scratch repo `/tmp/kpr-33-live`
(git init). Session `acp33-devin`. No PTY/Claude tests.

## Repro of the issue, now fixed

`kaola-acp.py devin start --model swe-2-max` (acp33-devin-start.json):

- `configured_options` now attest native `current_value`: model `swe-2-max`
  (value_name "SWE-2 Max"), mode `bypass` (value_name "Bypass Permissions").
- `acp_session_id`: `chambray-snap`.

`observe` (acp33-devin-observe.json) and `status` (acp33-devin-status.json):

- `session_meta.configOptions` current: `mode=bypass`, `model=swe-2-max` — the
  post-set native truth, not the launch snapshot.
- `initial_config_options` preserves the baseline distinctly:
  `mode=accept-edits`, `model=fusion-claude-fable-5-1-high-sidekick-swe-2-medium`
  (the exact stale values quoted in issue #33).

## Native update paths exercised

Holder `events.jsonl` for the session shows `config_options_applied` events with
`source=set_config_option` (model + mode sets) and `source=config_option_update`
(3 native notifications emitted by the real Devin adapter — the new merge path
ran on live traffic). `record.json` persists the same current/initial values.

## Session usable + exact stop

`send --text "Reply with exactly this token and nothing else: ACP33OK"`
(acp33-devin-send.json): `outcome=turn_completed`, `stop_reason=end_turn`,
`mutation_status=completed`, `final_text="ACP33OK"`.

`stop` (acp33-devin-stop.json): `stopped=true`, `residual_pids=[]`,
`agent_exit_code=0`. Final `record.json`: `state=stopped`, `agent_alive=false`.
`ps -p 8277,8278` post-stop: no such processes; `pgrep -fl acp33-devin`: none.

## Offline validation

- `tests/contract/test-issue-33-config-meta.py`: 9/9 PASS (initial baseline;
  set→native-not-requested; start --model flows to observe/status + record;
  config_option_update notification merge; failed set keeps prior state;
  missing-result no-fabrication; timeout keeps prior state; resume native truth
  + identity; absent configOptions not invented).
- `tests/contract/test-acp-contract.py`: 19/19 PASS. `test-acp-holder-continue.py`:
  29/29 PASS. Full `./scripts/validate.sh` exit 0. `render-skills.py --check` PASS
  (7 Skills regenerated via `--write`; `templates/grok-golden/` untouched).
