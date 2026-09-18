DECISION: ATTACH_AND_SEND
ASKED_FOR: n/a
RULE_CITED: "A **live** Host is attached in place — do not `start` again, even if its recorded name is not the new form, when that locator is unique." / "**Live Host** (exact platform/repo/session still serves, and `holder_instance_id` plus `acp_session_id` match the receipts): do not `start`. Continue on that holder. ... Do not replay the first handoff. Changing the outer Agent does not stop the Host or re-ask the full authorization set; apply only the user's latest change." / "On a **live** Host, apply only the user's latest change — do not re-ask the full set." / "Idle Host: `send` is enough. `--no-wait` means admitted, not delivered, and not project complete."
HANDOFF_TEXT: Update from the outer Agent (same run, same Host; not a new handoff).
priority=P0 (raised from P1)
Everything else is unchanged: goal, done/remaining, authorized_platforms, quota_concurrency, quota_account, quota_token, delivery_stop_boundary, and project_context all stay exactly as previously handed off. Do not expand authorization or quota on account of this change.
Continue the current run under the new priority.
TOKEN_QUOTA_TREATMENT: I did not restate, re-ask, refresh, or invent any token budget — this is a live-Host A→B attach, so the token figure stays whatever the Host already holds, named only as explicitly unchanged.
