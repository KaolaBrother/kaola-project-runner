# Host entry evidence (Issue #119, #126, #159)

Measurement record behind the loaded reference
`skills/kaola-project-runner/references/host-entry-matrix.md` (source
`templates/orchestrator/references/host-entry-matrix.md`). The loaded reference
keeps the entry fact, the per-platform entry and Skill roots, and the operative
notes; this page keeps the probe method, versions, negative controls, and the
deep-test narrative. Moved out of the loaded Skill by Issue #157 (PR-M1 for
the cross-platform matrix, PR-M2 for the ZCode native entry). The text below is
unchanged from the references as of `26cee00`, except that "this Mac" names the
maintainer Mac Studio, the codex note no longer names a `--stdin` flag the
Runner wrapper does not have (omit `--text` and pipe stdin instead), and Issue
#159 re-measures the kimi-cli row to both user roots (see the kimi-cli note).

## Probe method

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

## Matrix with probe and version (measured 2026-09-21, codex 2026-09-23, ACP, the maintainer Mac Studio)

| Platform | `host_skill_entry` | Probe; D3 step 2 / 5 | User Skill roots discovered | Version |
|---|---|---|---|---|
| zcode | `/kaola-project-runner` | E1 (#94) | `~/.zcode/skills`, `~/.agents/skills` | see ZCode native entry below |
| claude-code | `/kaola-project-runner` | E2; E2 / E2 | `~/.claude/skills` | bridge 0.1.0 |
| cursor-cli | `/kaola-project-runner` | E2; E2 / E2 | `~/.cursor/skills`, `~/.claude/skills`, `~/.codex/skills`, `~/.grok/skills`, `~/.agents/skills` | not advertised |
| grok | `/kaola-project-runner` | E2; E2 / E2 | `~/.grok/skills`, `~/.agents/skills`, `~/.claude/skills`, `~/.cursor/skills` | not advertised |
| devin | `/kaola-project-runner` | E1 (`Invoked skill`); E2 / E2 | `~/.config/devin/skills`, `~/.agents/skills`, `~/.claude/skills`, `~/.cursor/skills` | 0.0.0-dev |
| droid | `/kaola-project-runner` | E2; E2 / E2 | `~/.factory/skills`, `~/.agents/skills` | 0.220.0 |
| dsh | `/kaola-project-runner` | E2; E2 / E2 | `~/.agents/skills` | harness 0.0.1 |
| opencode | `/kaola-project-runner` | E1 (`skill` tool); E1+E2 / E2 | `~/.config/opencode/skills`, `~/.claude/skills`, `~/.agents/skills` | 2.0.11 |
| kimi-cli | `/skill:kaola-project-runner ` | E2; E2 / E2 | `~/.agents/skills`, `${KIMI_CODE_HOME:-~/.kimi-code}/skills` | 2.0.2 |
| codex | `$kaola-project-runner` | E2; E2 / E2 | `~/.codex/skills`, `~/.agents/skills` | codex-acp 1.13.0 (pin 1.13.1: see notes) |

## Notes

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
- **codex on codex-acp 1.13.1** (Issue #187, reported by the owning Host on
  2026-09-26, not re-measured in #187) - isolated E2 probes answered
  `SKILL-NOT-LOADED`; the E2 row above stays the 1.13.0 measurement. The live
  Codex Host the owner accepted then loaded the Skill by an explicit read of
  the installed `SKILL.md` and ran a working bind/wake loop: owner acceptance,
  not E1/E2 entry proof. No unconditional tool_call rule follows from it, and
  no Codex adapter change was made.
- **dsh** - E2 plus negative control.
- **kimi-cli (Issue #159 re-measure, Kimi Code 2.0.2+)** - the entry and both
  rows' lineage start at Issue #119 on Kimi Code 2.0.2 (E2; E2 / E2 for
  `~/.agents/skills`). Kimi Code CLI scans two user-level Skill roots per the
  upstream skill-location docs (moonshotai.github.io/kimi-code/en/customization/
  skills, retrieved 2026-09-24): the cross-tool `~/.agents/skills` and the
  Kimi-specific `${KIMI_CODE_HOME:-~/.kimi-code}/skills`, which moves with
  `$KIMI_CODE_HOME`. The kimi-specific root is additionally evidenced by fleet
  use on the 2026-09-24 failure this re-measure tracks (Issue #159): Workflow
  Skills deployed there by `install-kimi.sh --global` were loaded by the
  installed Kimi 2.0.2 while Runner Skills were absent from both roots. The
  root is documented and installed to; a dedicated live D3 for the added root
  (real-CLI session, E1/E2 + negative control) is the standing follow-up, kept
  pending here because it needs a real provider session. The installed binary
  on the maintainer Mac Studio is Kimi Code 2.0.2 (`~/.kimi-code/bin/kimi`);
  the `platforms/kimi-cli.yaml` `cli=2.1.0` record is the un-probed optional
  same-commit record (bundle-153), not a re-measure.
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

## ZCode native entry (Issue #94)

The loaded reference `zcode-native-skill-entry.md` keeps the one entry, the
per-entry-point list, the discovery roots and the boundaries. The measured
facts behind them follow. The discovery-root and no-compaction-hook facts were
measured on ZCode 3.12.3 and were not re-verified on the 3.14.x App / 0.16.9
CLI line recorded in `platforms/zcode.yaml` (#154).

### Discovery roots as measured

Native invocation needs the generated `kaola-project-runner` Skill installed
where the Host session discovers skills. Verified against the installed
ZCode 3.12.3 — in its `createSkillsService` binary code and live through
injected skill metadata — the install-relevant **default** roots are the
workspace `<repo>/.zcode/skills/` and `<repo>/.agents/skills/`, the
user-level `~/.zcode/skills/` and `~/.agents/skills/`, plus the same two
roots on each ancestor directory up to the workspace boundary. The defaults
are not the whole discovery surface: `skills.roots` in
`~/.zcode/cli/config.json` adds configured skill roots scanned as
project-scope roots (live-verified); `plugins.dirs` in the same file
adds plugin roots whose `skills/` are scanned too (a plugin skill
surfaces namespaced as `<plugin>:<skill>` and stays loadable by its
plain name — live-verified); plugin cache roots remain a separate
mechanism, not an install target.
`--runtime zcode` installs to `~/.zcode/skills/`; `--skills-dir` accepts
any of these roots, e.g. `<repo>/.agents/skills`. A `--skills-dir` outside
every discovered root — default or configured — still works for an agent
that reads the file itself, but a ZCode Host does not read the file: the
first line then arrives as plain text. If the first beat's `capture` shows
no `Skill` tool_call, the Skill is not installed where this session
discovers it: report that fact and install it properly; do not fall back
to reading `SKILL.md` by hand.

### Facts that did not change

- ZCode 0.16.5/3.12.3 has no compaction hook (`SessionStart` fires on
  `startup`/`resume` only) and surfaces no compaction through ACP:
  `observe`/`capture` show none and `context_usage` stays null.
- `/compact` and the `session/compact` RPC write the same `compaction` /
  `context_compaction` `part` rows in `db.sqlite`. A read-only cursor on
  that table remains an optional diagnostic for a compaction you did not
  order — never a per-send check, a transport gate, or a ledger.
- Auto-compaction is real and equally silent; episodes carry
  `trigger:"auto"` on the same rows.
- Workspace `AGENTS.md` content is still resolved into the per-request
  prefix and still survives compaction — a true runtime fact, now only
  background; ordinary Agents in the same repo carry no Host instruction
  at all.

### Evidence

Verified live (installed ZCode 3.12.3, repo adapter 0.3.3):

- Real GLM model: `/kaola-project-runner` produces a native `Skill`
  tool_call; a manual `/compact` then `/kaola-project-runner` produces a
  **new** `Skill` tool_call returning a Skill-body marker — not a manual
  `read` (Issue #94 matrix).
- Command plus trailing prompt text: the `Skill` tool_call fires and the
  rest of the prompt is handled normally — the form the heartbeat envelope
  uses.
- Real `trigger:"auto"` compactions (isolated mock provider, declared small
  `contextWindow`, scratch `HOME`): the request after each completed
  compaction still carries the `/<skill-name>` invocation rule and the
  `kaola-project-runner` skill metadata on the wire.
- Discovery roots (Issue #94 review fix): the installed 3.12.3 binary
  resolves workspace `.zcode/skills` and `.agents/skills`, user
  `~/.zcode/skills` and `~/.agents/skills`, plus both roots on ancestor
  directories; a scratch-HOME live probe injected the
  `kaola-project-runner` metadata from each `.agents/skills` root.
  Configured roots add more: `skills.roots` in `~/.zcode/cli/config.json`
  is passed to the skills service as `extraRoots` — the same probe
  injected the metadata with `file:` at the configured root — and
  `plugins.dirs` makes the runtime scan a plugin dir's `skills/`
  (`kpr-extra:kaola-project-runner`, loadable as `kaola-project-runner`).
- Composite interrupt steer (Issue #94 re-review): the holder's
  `--steer-mode interrupt` resend carries the Agent's text verbatim on a
  genuinely new turn — contract-tested end-to-end (cancel confirmed, new
  prompt admitted, bytes unchanged) on Host-shaped and ordinary sessions
  alike; it is not a Host recovery entry.

Not verified: real-model *behaviour* after a genuine auto-compaction — the
catalog GLM models are 1M-window and forcing one is beyond bounded cost —
any compact-specific ACP event, because none exists, and a `Skill`
tool_call from a busy `steer` guide, because steer forwards the guide into
the running turn and no re-invocation is claimed (a caller-supplied
`/kaola-project-runner` first line on an interrupt resend follows the
same verified entry mechanism). The pre-0.3.3
installed adapter exits against ZCode 3.12.3; update the install rather
than the mechanism.
