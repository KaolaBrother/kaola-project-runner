DECISION: START

ASKED_FOR: n/a

RULE_CITED: SKILL.md "Extract once": "From the user and existing Git, Workflow, Issue, and Runner records collect: goal; already-done and remaining work; authorized worker platforms/members and counts and concurrency; the quota the user actually gave, each figure in its own unit; priority; delivery and stop boundary; the explicit project path." / "On a **new** Host, missing, conflicting, or expired key values must be confirmed before `start`." / "Do not invent platforms, fuse quota units, raise quota, treat an unspecified quota as unlimited, reuse a stale quota, or expand authorization."
handoff.md step 4: "A new Host (first start, or after failed `--resume`) needs current authorization **before** `start`: goal and remaining work; allowed worker platforms/members; counts and concurrency; the quota given, in its own units; priority; delivery and stop boundary." step 5: "With step 4 complete and no live Host: start once under `$HOST` at `$PROJECT`. Confirm `session`/`repo`/`acp_session_id`/`holder_instance_id` from the start receipt, then send the first handoff."
handoff.md handoff text: "quota units never merge; `unspecified` is not unlimited".

HANDOFF_TEXT:
(Preceded by: `"$ZCODE" status --repo "$PROJECT" --session "zcode-KPR-orchestrator-main"` returning no session, then a single
`"$ZCODE" start --repo "$PROJECT" --session "zcode-KPR-orchestrator-main"`, confirming session/repo/acp_session_id/holder_instance_id from the start receipt. Generic/Codex host: no Grok Bot locator attestation. Then:)

Load <skills>/kaola-project-runner/SKILL.md (Project Runner) and follow it.
You are the ZCode Host for this run.
platform=zcode session=zcode-KPR-orchestrator-main repo=/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner
goal=Issue #91 — fix relay bracketed-paste truncation
done=root cause already located
remaining=implement the fix + regression tests
authorized_platforms=zcode:1
quota_concurrency=at most 1 worker at a time
quota_account=40 conversations remaining
quota_token=200000 tokens; stop when exhausted
priority=P1
delivery_stop_boundary=freeze the candidate, then stop and wait for the user's review
project_context=canonical Git root /Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner; project short code KPR
Finish planning, worker dispatch, notification binding, heartbeat, acceptance,
and Workflow close-out internally. Do not wait for the outer Agent to bind
workers, paths, scheduling, or heartbeat. Missing authorization stays missing:
do not expand it.

TOKEN_QUOTA_TREATMENT: The user gave an explicit, unit-clear token cap, so I carried it verbatim as its own field `quota_token=200000 tokens; stop when exhausted`, kept separate from `quota_account=40 conversations` and `quota_concurrency=1`, without merging, converting, or raising any of them.
