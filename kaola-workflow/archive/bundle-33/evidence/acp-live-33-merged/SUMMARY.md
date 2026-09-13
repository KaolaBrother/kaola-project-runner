# Live evidence — issue #33 on merged candidate (527ecba+458cdff)

Session: acp33-devin2 | native acp_session_id: aerial-turnip | devin CLI 3000.10.21
Repo: /private/tmp/kpr-33-live | holder dir receipts copied alongside.

- start --model swe-2-max -> ready (start.json: set receipts attest native currentValue)
- observe/status: session_meta.configOptions CURRENT model=swe-2-max mode=bypass;
  initial_config_options preserves baseline model=fusion-claude-fable-5-1-high-sidekick-swe-2-medium mode=accept-edits
- events.jsonl: 5 config_options_applied (set_config_option results + native config_option_update notifications)
- send: "Reply with exactly this token and nothing else: ACP33MERGED" -> final_text ACP33MERGED, stop_reason end_turn
- stop: stopped=true residual_pids=[] agent_exit_code=0; record state=stopped; no residual processes
