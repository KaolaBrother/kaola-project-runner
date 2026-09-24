# Host entry matrix

Issue #119. Which platforms can run this Skill as an event-driven Host, the
first line that opens every Host turn there, and where the Skill must be
installed. [zcode-native-skill-entry.md](zcode-native-skill-entry.md) stays the
ZCode detail; this file is the cross-platform table. Probe method, versions and
negative controls: `docs/host-entry-evidence.md` in the Project Runner checkout.

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
measurement: a row is filled only from a live run with trigger evidence. Since
#126 every shipped row has an entry; the rule holds for any platform without one.

## Matrix (measured on the maintainer Mac Studio)

| Platform | `host_skill_entry` | User Skill roots discovered |
|---|---|---|
| zcode | `/kaola-project-runner` | `~/.zcode/skills`, `~/.agents/skills` |
| claude-code | `/kaola-project-runner` | `~/.claude/skills` |
| cursor-cli | `/kaola-project-runner` | `~/.cursor/skills`, `~/.claude/skills`, `~/.codex/skills`, `~/.grok/skills`, `~/.agents/skills` |
| grok | `/kaola-project-runner` | `~/.grok/skills`, `~/.agents/skills`, `~/.claude/skills`, `~/.cursor/skills` |
| devin | `/kaola-project-runner` | `~/.config/devin/skills`, `~/.agents/skills`, `~/.claude/skills`, `~/.cursor/skills` |
| droid | `/kaola-project-runner` | `~/.factory/skills`, `~/.agents/skills` |
| dsh | `/kaola-project-runner` | `~/.agents/skills` |
| opencode | `/kaola-project-runner` | `~/.config/opencode/skills`, `~/.claude/skills`, `~/.agents/skills` |
| kimi-cli | `/skill:kaola-project-runner ` | `~/.agents/skills`, `${KIMI_CODE_HOME:-~/.kimi-code}/skills` |
| codex | `$kaola-project-runner` | `~/.codex/skills`, `~/.agents/skills` |

Notes:

- **kimi-cli** - the entry ends with one space. Kimi advertises Skills as
  `skill:<name>` commands and reads the command name up to the first space, so
  `/skill:kaola-project-runner` followed directly by a newline is answered
  `Unknown ACP command`; bare `/kaola-project-runner` is unknown too.
- **kimi-cli (Issue #159)** - Kimi Code CLI scans BOTH user-level Skill roots:
  the cross-tool `~/.agents/skills` (shared with dsh) and the Kimi-specific
  `${KIMI_CODE_HOME:-~/.kimi-code}/skills`, which moves with `$KIMI_CODE_HOME`
  (upstream docs; measured lineage starts at Issue #119 on Kimi Code 2.0.2 and
  is re-measured for 2.0.2+ in docs/host-entry-evidence.md). `--runtime
  kimi-cli` installs into both roots, each with its own receipt set; reinstall
  every root the Host reads, and uninstall withdraws the kimi-cli reference
  from both.
- **codex** (#126) - the entry is Codex's `$` Skill mention, as advertised in
  `available_commands`; not `/`. A shell must pass the entry single-quoted, or
  omit `--text` and pipe stdin: in double quotes `$kaola` expands. Like every
  Host, a codex Host's beat rewrites `.kaola/heartbeat-prompt.json`; Codex's own
  timer serves only a Codex supervisor that is not a Host.
- **dsh** has an entry despite advertising no commands: `/kaola-project-runner`
  loads the Skill from `~/.agents/skills`.
- Project-level roots are discovered too (`<repo>/.claude/skills`,
  `.agents/skills`, and each platform's own dot-directory), except grok, which
  showed only user roots.
- A Host start compares the worker Skills in its own platform's discovered roots
  with its build before it starts (#105), the same check a ZCode Host runs. A
  same-named older main Skill in a user root wins over a project copy (seen on
  cursor-cli), so the start also compares every main Skill in those roots
  (#121) and refuses `main-skill-build-skew` naming the stale path. Reinstall
  every root the Host reads.
- **opencode** - every ACP `start` receipt carries `effective_selection`
  (`effective_model`, `effective_effort`): the agent's own advertised
  `currentValue`. An explicit `--model` / `--effort` the agent does not report
  is refused (`reason: explicit-selection-unverified`): the session is stopped
  before `start` returns, `mutation_performed: false`, and no other model is
  substituted. Give an opencode Host the explicit selection the operator
  configured. The Runner never picks it.
