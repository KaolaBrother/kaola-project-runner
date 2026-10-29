# Issue #423: what a Devin `_cognition.ai/compaction` pair means

Measured 2026-10-29 on the MacBook (Devin CLI 3000.11.92 `7f4e64980e22`), read-only, from the
local holder event logs `/tmp/kaola-501/devin/*/*/events.jsonl*` (87 Devin record directories, 48
with at least one pair) and the committed #264 acceptance logs under
`docs/evidence/host-compaction/edge-devin-20261006-*` (Devin 3000.11.3).

## Census

For every `_cognition.ai/compaction` `completed` notification, `used` before is the last
`usage_update.used` before it, and `used` after is the first `usage_update.used` after it.

| completed notification | count | context after vs before |
|---|---:|---|
| carries a non-empty string `summary` (17,181–32,120 chars) | 84 | 83 shrink to ≤ 0.6× (typically 183–195k → 30–44k of 262k); 1 has no earlier `usage_update` (first reading after: 41,399) |
| no `summary` key | 688 | 681 no drop (`used` keeps rising); 7 drop, **every one at a context-window switch** (`size` 1,000,000 ↔ 262,000), 0 unexplained |

Every `started` (772) has no `summary`. Every pair is `started` and `completed` at the same
millisecond. The two committed #264 Devin 3000.11.3 completions also carry `summary` (9,299 and
20,455 chars) and shrink the context to 20,716 / 28,851.

Conclusion: on 3000.11.92 Devin also sends a summary-less started/completed pair on ordinary agent
steps, and the context does not shrink. A real context compaction is the `completed` that carries
the conversation `summary`. A context-shrink rule would misread the 7 window switches and would need
to wait for a later `usage_update`. The `summary` rule decides from the one notification.

## Bounded excerpts

Per-step pair, `devin-KPR-i416-platform` (one of 53 in that turn; `used` 183,494 → 250,329 across
all 53):

```json
{"cursor": 3285, "kind": "compact_reload_detected", "role": "elite", "session_id": "glowing-mandrill", "signal": {"jsonrpc": "2.0", "method": "_cognition.ai/compaction", "params": {"sessionId": "glowing-mandrill", "status": "completed"}}, "source": "devin-compaction"}
```

Real compaction, `devin-KPM-i596-repair1` cursor 706 (summary truncated here):

```json
{"method": "_cognition.ai/compaction", "params": {"sessionId": "flawless-crowberry", "status": "completed", "summary": "Full conversation history saved at /Users/ylpromax5/.local/share/devin/cli/summaries/history_cc4e8ca0d2dc47c9.md.\nSummary:\n<summary>\n1. Request and Intent: ..."}}
```

Window switch without compaction, `devin-KPR-i421-retire-evidence`:

```text
6775 usage_update used=314259 size=1000000
6777 _cognition.ai/compaction started
6778 _cognition.ai/compaction completed        (no summary)
6780 usage_update used=210222 size=262000
```

## The incident this explains

`devin-KPR-i416-platform`: turn 5142 ended (`delegator`, `end_turn`). The holder had counted the
per-step pairs as owed compactions, so at 5144 it sent `compact_reload_delivered`. The seat then
ran a full reload turn (new `turnRequestId` 0885d236, 13,530 input tokens), which ended at 5309
(`self`, `turn_completed`) with no project work.
