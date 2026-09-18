DECISION: ATTACH_AND_SEND
ASKED_FOR: n/a
RULE_CITED: SKILL.md: "On a **live** Host, apply only the user's latest change — do not re-ask the full set." / "A **live** Host is attached in place — do not `start` again, even if its recorded name is not the new form, when that locator is unique." / "Exact Host `stop` and live attach use `holder_instance_id` from the existing receipt (`--expected-holder-instance-id`); a different holder is not that Host." handoff.md step 2: "**Live Host** (exact platform/repo/session still serves, and `holder_instance_id` plus `acp_session_id` match the receipts): do not `start`. Continue on that holder. ... Do not replay the first handoff. Changing the outer Agent does not stop the Host or re-ask the full authorization set; apply only the user's latest change." handoff.md: "Idle Host: `send` is enough." SKILL.md: "A quota unit the user never gave is not a missing key value — carry it as unspecified and start".
HANDOFF_TEXT: "$ZCODE" send --repo "$PROJECT" --session "zcode-KPR-orchestrator-main" --expected-holder-instance-id "hold_a91c" --no-wait --text '<below>'

Outer Agent changed (A -> B); this Host is unchanged and stays live. Update only:
priority=P0 (was P1)
Everything else unchanged: goal, done/remaining, authorized_platforms, quota_concurrency, quota_account, quota_token, delivery_stop_boundary, project_context all stay exactly as previously handed off. No new authorization, no quota change.
Continue from your current frontier; do not re-plan from zero, do not re-dispatch in-flight workers, and keep owning heartbeat, acceptance, and Workflow close-out internally.
TOKEN_QUOTA_TREATMENT: I did nothing about a token budget — the user gave no token figure and this is a live Host, so no quota value is re-sent, re-asked, raised, fused with another unit, or inferred as unlimited; whatever quota_token the Host already holds (given or `unspecified`) stands unchanged.
