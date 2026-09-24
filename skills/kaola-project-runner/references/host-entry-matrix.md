# Host entry matrix

Issue #119. Which platforms can run this Skill as an event-driven Host, the
first line that opens every Host turn there, where the Skill must be installed,
and the evidence behind each row. [zcode-native-skill-entry.md](zcode-native-skill-entry.md)
stays the ZCode detail; this file is the cross-platform table.

## The entry fact

`host_skill_entry` in `platforms/<id>.yaml` is the complete first line of every
turn-opening Host prompt: the startup handoff, a resume or attach round, and the
heartbeat carrier the Host holder builds (`kaola-host-notify/1`, whose second
line names `(<runtime_name> Host)`). The rest of the prompt follows on the next
line. It is an entry fact, never a model or tier field: a Host `start` resolves
`--tier` / `--model` / `--effort` exactly as a worker `start` on that platform
does, and `default` stays that platform's own default (opencode: the CLI's
native opening model, not overridden).

An empty value means no measured entry, and that platform cannot be a Host
(#122, owner ruling: fail closed, no plain-text first line). A Host-named `start`
on it, a worker `start` it dispatches (`heartbeat_host_source:
dispatcher-no-carrier`), and a start whose `KAOLA_ACP_HEARTBEAT_HOST` names it
all refuse `reason: host-entry-unsupported` before any record, socket or holder
exists (`mutation_performed: false`, exit 1); its holder still refuses
`worker_event`. As an ordinary worker it is unaffected. Admission is the
measurement: fill the entry from a row below, then it may host. Since #126
every shipped row has an entry; the rule holds for any platform without one.

A row is filled only from a live run with trigger evidence:

- **E1** - the ACP event stream shows a Skill tool_call naming
  `kaola-project-runner`.
- **E2** - in a fresh session, with no tool call, the reply quotes a sentence
  that exists only in the installed Skill body and not in the prompt.

Every filled row also has a negative control: the same fresh-session question
without the entry line answered `SKILL-NOT-LOADED` with no tool call, and a
deep test (D3) where the handoff (step 2) and the carrier-woken beat (step 5)
each produced E1 or E2. In that turn no tool read or grepped the main Skill, and
the quoted sentence exists only in this build.

## Matrix (measured 2026-09-21, codex 2026-09-23, ACP, the maintainer Mac Studio)

| Platform | `host_skill_entry` | Probe; D3 step 2 / 5 | User Skill roots discovered | Version |
|---|---|---|---|---|
| zcode | `/kaola-project-runner` | E1 (#94) | `~/.zcode/skills`, `~/.agents/skills` | see zcode-native-skill-entry.md |
| claude-code | `/kaola-project-runner` | E2; E2 / E2 | `~/.claude/skills` | bridge 0.1.0 |
| cursor-cli | `/kaola-project-runner` | E2; E2 / E2 | `~/.cursor/skills`, `~/.claude/skills`, `~/.codex/skills`, `~/.grok/skills`, `~/.agents/skills` | not advertised |
| grok | `/kaola-project-runner` | E2; E2 / E2 | `~/.grok/skills`, `~/.agents/skills`, `~/.claude/skills`, `~/.cursor/skills` | not advertised |
| devin | `/kaola-project-runner` | E1 (`Invoked skill`); E2 / E2 | `~/.config/devin/skills`, `~/.agents/skills`, `~/.claude/skills`, `~/.cursor/skills` | 0.0.0-dev |
| droid | `/kaola-project-runner` | E2; E2 / E2 | `~/.factory/skills`, `~/.agents/skills` | 0.220.0 |
| dsh | `/kaola-project-runner` | E2; E2 / E2 | `~/.agents/skills` | harness 0.0.1 |
| opencode | `/kaola-project-runner` | E1 (`skill` tool); E1+E2 / E2 | `~/.config/opencode/skills`, `~/.claude/skills`, `~/.agents/skills` | 2.0.11 |
| kimi-cli | `/skill:kaola-project-runner ` | E2; E2 / E2 | `~/.agents/skills` | 2.0.2 |
| codex | `$kaola-project-runner` | E2; E2 / E2 | `~/.codex/skills`, `~/.agents/skills` | codex-acp 1.13.1 |

Notes:

- **kimi-cli** - the entry ends with one space. Kimi advertises Skills as
  `skill:<name>` commands and reads the command name up to the first space, so
  `/skill:kaola-project-runner` followed directly by a newline is answered
  `Unknown ACP command`; bare `/kaola-project-runner` is unknown too.
- **codex** (#126) - the entry is Codex's `$` Skill mention, as advertised in
  `available_commands`; not `/`. Until 2026-09-23 every turn answered a
  usage-limit notice, so codex stayed refused. Measured then on gpt-6-sol/high:
  E2 in a fresh session, and the negative control answered `SKILL-NOT-LOADED`.
  That E2/D3 row was measured on codex-acp 1.13.0; the pinned adapter moved
  record-only to 1.13.1 with `@openai/codex@0.156.1` on 2026-09-24 (Pink
  class-2 report, Issue #153), with no new live run. D3 as below with a codex
  worker (under the shadow `HOME` dsh had no
  credentials and claude-code no login). The roots column is #119's 1.11.0
  probe; #126 held only `~/.codex/skills`. A shell must pass the entry
  single-quoted, or omit `--text` and pipe stdin: in double quotes `$kaola` expands. Like every Host, a codex Host's beat
  rewrites `.kaola/heartbeat-prompt.json`; Codex's own timer serves only a
  Codex supervisor that is not a Host.
- **dsh** has an entry despite advertising no commands: `/kaola-project-runner`
  loads the Skill from `~/.agents/skills` (E2 plus negative control).
- Project-level roots were discovered too (`<repo>/.claude/skills`,
  `.agents/skills`, and each platform's own dot-directory), except grok, which
  showed only user roots.
- A Host start compares the worker Skills in its own platform's discovered roots
  with its build before it starts (#105), the same check a ZCode Host runs. A
  same-named older main Skill in a user root wins over a project copy (seen on
  cursor-cli), so the start also compares every main Skill in those roots
  (#121) and refuses `main-skill-build-skew` naming the stale path. Reinstall
  every root the Host reads.
- D3, every non-ZCode row (2026-09-21; codex 2026-09-23): run under a shadow `HOME` whose Skill roots
  held only this build and an isolated `KAOLA_ACP_RECORD_ROOT`. Each Host
  started on its default tier (opencode on the explicit
  `opencode-go/deepseek-v4.1-flash` / `max`). The worker bound to it
  (`heartbeat_host_source: dispatcher`), and each delivered carrier's
  fingerprint equals a rebuild opening with that row's entry and
  `(<runtime_name> Host)`. The woken beat read the worker, exact-stopped it,
  rewrote `.kaola/heartbeat-prompt.json` and ended. Every Host stop returned
  `residual_pids: []`, and `kaola-acp-sweep --root` on that record root
  reported no residue.
- A dsh worker could not start inside a dsh Host (ACP `initialize` failed, agent
  exit 1). The dsh row's D3 used a claude-code worker; dsh as Host is unaffected.
- droid's first D3 attempt hit the account's 5-hour Droid Core quota (HTTP
  402), a quota and not a capability; the run after the reset passed.

## OpenCode model and effort (H2)

The account configures `opencode-go/deepseek-v4.1-flash` in
`~/.config/opencode/opencode.json`, with effort `max` only in the TUI state file.
Measured on 2.0.11:

- With no `--model`, ACP `session/new` reports `currentValue`
  `opencode/deepseek-v4.1-flash` (provider `opencode`, not `opencode-go`) and
  effort `default`; the first prompt fails `-32603 provider.no-route`. So ACP
  resolves the configured model id under another provider (contradiction 1), and
  the TUI variant `max` is not inherited (contradiction 2).
- With `--model opencode-go/deepseek-v4.1-flash --effort max`, the agent reports
  exactly those values and a real prompt round trip completes (`end_turn`).

Every ACP `start` receipt carries `effective_selection` (`effective_model`,
`effective_effort`): the agent's own advertised `currentValue`. For opencode, an
explicit `--model` / `--effort` the agent does not report is refused
(`reason: explicit-selection-unverified`): the session is stopped before
`start` returns, `mutation_performed: false`, and no other model is substituted.
Give an opencode Host the explicit selection the operator configured. The
Runner never picks it.
