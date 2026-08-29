# Five-runtime live smoke — 2026-08-29

This record covers the real-CLI validation for Issue #1. Each runtime was launched in one exact,
Runner-owned tmux main conversation, received one complete Grok-aligned project-run prompt, and was
asked to load `workflow-next` under a read-only validation boundary. The validator did not own the
active Issue #1 claim and therefore had no authority to edit, claim, finalize, or close work.

## Runtime matrix

| Platform | Version | Exact-session result | Workflow result | Shutdown evidence |
|---|---|---|---|---|
| Grok CLI | `1.0.13 (5e9a58528b76)` | Complete prompt received as one input | Installed `workflow-next.md` loaded; live state and mission list inspected; stopped at the existing Issue #1 ownership boundary without mutation | Graceful quit returned `result=stopped`; follow-up status returned `present=false`, `result=absent` |
| Claude Code | `2.1.246` | Complete prompt reached the trusted project TUI | Command receipt passed, then execution stopped at `Login expired` / `Not logged in`; no Workflow execution is claimed | `/exit` completed and the exact session was absent |
| OpenCode | `1.18.23` | Complete multiline prompt arrived as one editor event after the bracketed-paste transport fix | Installed `workflow-next` command was read; read-only Step 1 completed in an isolated clean repository with no remotes and no open Issues | Graceful stop completed; exact session absent; isolated repository remained clean |
| Kimi CLI | `0.39.1` | Complete prompt reached the trusted repository TUI | TUI reported `Used Skill (workflow-next)` and `Activated skill: workflow-next`; read-only startup reached the ownership inspection boundary | Stream was interrupted before mutation, `/exit` completed, and the exact session was absent |
| Cursor CLI | `2026.08.25-3e8eec8` | Complete prompt reached the Cursor agent after official project command materialization | TUI reported that the materialized `workflow-next` was found and loaded; inspection remained read-only | Graceful stop completed; exact session absent; official uninstall removed all 17 managed files and preserved zero foreign files |

Claude Code is intentionally a receipt-only result because this machine has no usable Claude account.
Authentication-blocked receipt must not be presented as successful Kaola Workflow execution.

## Observed adapter repairs

- OpenCode exposed that raw multiline tmux paste could become several queued turns. The neutral core
  now requests terminal bracketed-paste wrapping and submits the payload only after the TUI event loop
  receives it. The repeated smoke delivered the prompt once and completed the read-only startup.
- Kimi exposed a trust screen, a real `thinking...` busy state, and a
  `session_<uuid>` runtime session identifier. Detection now follows those observed states instead of
  guessing from Grok behavior.
- Cursor could not discover `workflow-next` from ambient user state alone. A new exact run now invokes
  the installed Kaola Cursor authority's receipt-backed project materialization before tmux creation.
  The materializer's own exact path, hash, and mode are verified before it runs; foreign collisions
  fail before a session exists, and cleanup remains owned by that authority.
- Final review reproduced a scrollback-spoofed shell under otherwise matching tmux markers. The core
  now binds the exact resolved runtime binary at argv[0] or interpreter argv[1] plus the platform's
  observed title/current-command predicate; a runtime path passed as later shell argument is rejected.
  Kimi's fixed `kimi-code` process title additionally requires tmux's live `node` command. All five
  spoof cases refuse input, and ordinary stop preserves unresolved `HUMAN_DECISION_REQUIRED` sessions.

These are adapter and transport corrections. They do not rewrite or reinterpret the Grok Skill,
project/PR prompts, four task modes, heartbeat, scheduler, or closing protocol.

## Regression and residue evidence

`./scripts/validate.sh` passed the deterministic renderer, all five Skill validators, immutable Grok
golden inventory, Grok compatibility suite, lifecycle cleanup contract, installer migration, neutral
tmux ownership, five adapters, and live-smoke adapter contracts. Shell syntax, Python compilation,
`git diff --check`, and a final renderer drift check also passed.

After the five real sessions, no tmux session matching `^kpr-issue1-smoke-` remained. No detached
project intake or recurring Runner scheduler was started by these one-shot validations.

After the final process-identity hardening, all five real CLIs were also reopened in exact
`kpr-issue1-identity-*` sessions and proved `process_match=true` plus `tui_detected=true`. Each exact
session was stopped and became absent. Cursor's repeated official project uninstall reported
`removed=17`, `preserved=0`, followed by zero `.cursor` residue.
