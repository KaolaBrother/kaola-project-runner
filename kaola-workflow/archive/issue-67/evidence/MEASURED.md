# Issue #67 measurement

Isolated adapter-stdio probe only. No tmux, no other sessions, no global
install, no credential dump. Sentinel:
`kaola-workflow/issue-67/evidence/live-sentinel/MARKER.txt`.

## Other ACP platform (Claude Code)

Source: `archive/issue-65/evidence/live/claude-code-6-capture.json`
(snapshot: `compare/claude-code-acp-issue-65-tool-calls.json`).

Live `tool_call` union keys: `kind`, `rawInput`, `sessionUpdate`, `status`,
`title`, `toolCallId`. `rawInput` carried `{command, description}`.
`locations` was absent on that capture.

## ZCode upstream (CLI 0.16.5 app-server)

Runtime: `KAOLA_ZCODE_ENTRY=/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs`,
`KAOLA_ZCODE_NODE=/opt/homebrew/bin/node`. Prompt: read `MARKER.txt` only.

`live/zcode-upstream-events.before.json` (and the matching after-fix dump):

- `model.streaming` `kind: tool_call` **does** carry `input: {file_path: <marker>}`.
- `tool_input_start` / `tool_input_delta` / `tool_input_end` appear first and
  have no `input`.
- `tool.updated` `scheduled` omits `input` and has `inputOmitted` / `inputRef`
  / `inputByteLength` instead. The adapter does **not** follow `inputRef`.

## ZCode ACP before the translator change

`live/zcode-acp-tool-calls.before.json`: three `tool_call` updates
(pending / in_progress / completed) with only
`kind`, `title`, `status`, `toolCallId`. No `rawInput`, no `locations`.
The assistant still returned the marker line, so the Read happened.

Issue #66 capture `03-host-startup-capture.json` had the same five-field shape
on 15 updates.

## ZCode ACP after the translator change

`live/zcode-acp-tool-calls.json`: the same three statuses now include
`rawInput.file_path` and `locations[0].path` equal to the sentinel marker
file. `leftover_pids: []`. No credential appeared in the dump.

Later outer review dropped plaintext `command` from persistence. That live
Read capture had no command field — only `file_path` — so the path evidence
still matches the current translator. Execute cards keep kind/title/status
without a command transcript.
