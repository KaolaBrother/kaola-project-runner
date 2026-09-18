DECISION: START

ASKED_FOR: n/a

RULE_CITED: "A new Host (first start, or after failed `--resume`) needs current authorization **before** `start`: goal and remaining work; allowed worker platforms/members; counts and concurrency; account and token quota as separate figures; priority; delivery and stop boundary." and "With step 4 complete and no live Host: start once under `$HOST` at `$PROJECT`. Confirm `session`/`repo`/`acp_session_id`/`holder_instance_id` from the start receipt, then send the first handoff." Also: "Handoff text (concurrency, account quota, and token budget stay three numbers)" and "Do not invent platforms, fuse quota units, raise quota, reuse a stale quota, or expand authorization."

HANDOFF_TEXT:
Load <skills>/kaola-project-runner/SKILL.md (Project Runner) and follow it.
You are the ZCode Host for this run.
platform=zcode session=zcode-KPR-orchestrator-main repo=/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner
goal=Issue #91 — fix relay bracketed-paste truncation
done=root cause located
remaining=implement the fix and add regression tests
authorized_platforms=zcode:1
quota_concurrency=1
quota_account=40 conversations remaining
quota_token=200000 tokens; stop when exhausted
priority=P1
delivery_stop_boundary=freeze the candidate, then stop and wait for the user's review
project_context=canonical Git root /Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner; project short code KPR; no live Host existed (Runner status returned no session), so this is a new ACP session started for this run
Finish planning, worker dispatch, notification binding, heartbeat, acceptance,
and Workflow close-out internally. Do not wait for the outer Agent to bind
workers, paths, scheduling, or heartbeat. Missing authorization stays missing:
do not expand it.

TOKEN_QUOTA_TREATMENT: I carried the 200000-token cap through verbatim as its own `quota_token` figure — kept separate from `quota_concurrency=1` and `quota_account=40 conversations`, neither fused, converted, nor raised.
