# Issue #113 — acceptance (c) draft for the closing comment

Prepared by the #113 implementation seat for the Host to place in the closing comment at finalize
time. Not posted. The commands are read-only (`sqlite3 -readonly`) and the figures below were
measured on 2026-09-21 against the real `~/.zcode/cli/db/db.sqlite`.

---

**Count metric (read-only).** ZCode records every model request in
`~/.zcode/cli/db/db.sqlite` `model_usage`. `session.directory` attributes each request to a
project. Output-token-max stops can be counted per project with:

```sh
DB=~/.zcode/cli/db/db.sqlite

# retained window, and how close any request came to the 128K output ceiling
sqlite3 -readonly -header "$DB" "select count(*) as rows, datetime(min(started_at)/1000,'unixepoch') as first_utc, datetime(max(started_at)/1000,'unixepoch') as last_utc, max(output_tokens) as max_output_tokens, round(100.0*max(output_tokens)/128000,1) as pct_of_128k from model_usage;"

# finish_reason distribution, all projects
sqlite3 -readonly -header "$DB" "select coalesce(finish_reason,'(null)') as finish_reason, count(*) as n from model_usage group by 1 order by 2 desc;"

# output-limit finishes per project (the app's own isOutputTokenLimitFinishReason set)
sqlite3 -readonly -header "$DB" "select s.directory, m.finish_reason, count(*) as n from model_usage m join session s on s.id = m.session_id where m.finish_reason in ('length','max_tokens','max_output_tokens','model_context_window_exceeded') group by 1,2 order by 3 desc;"

# the exhaustion ModelError (thrown after 3 auto-continues) per project
sqlite3 -readonly -header "$DB" "select s.directory, count(*) as n from model_usage m join session s on s.id = m.session_id where m.error_code = 'model_output_limit_exceeded' or m.error_message like '%exceeded the output token maximum%' group by 1 order by 2 desc;"
```

**Current result: zero occurrences.** The retained history holds 3,773 requests, from
2026-09-16 09:46:41 to 2026-09-21 02:37:38 UTC:

- Finish reasons: `tool-calls` 3,053, `stop` 618, null 102.
- **Zero** output-limit finishes on any project.
- **Zero** exhaustion errors.
- **Zero** `context_exceeded` rows.
- The only errors are `network_error` 93, `unknown` 3 and `cancelled` 1.
- The largest single response was 14,558 output tokens, 11.4% of the 128,000-token ceiling.

This confirms the 2026-09-21 investigation over a longer window (3,661 rows then). The DB stores
the *normalised* finish reason, so an output-limit stop would show up here as `length`. The raw
provider tokens are included only as a defensive net.

**What changed, and what did not.** This release does not fix a confirmed defect. There was no
on-disk output-token-max stop to fix, and "one project frequently hits the output maximum" stays an
unconfirmed observation. What #113 fixes is visibility: the ZCode adapter used to report such a
stop as `refusal` (or `end_turn`), so it could only be found in this DB. The adapter now reports
ACP `stopReason: "max_tokens"`, and the Runner keeps it in three places:

- the turn receipt;
- `record.json` `last_prompt.stop_reason`;
- a new `turn_ended` line in `events.jsonl`.

Any future occurrence can now be attributed per project both from Runner receipts and from the
queries above. It is no longer invisible when it happens.
