# Kaola Project Runner

**Let one agent work through another agent's CLI.**

Kaola Project Runner provides seven self-contained **worker** Agent Skills for **Claude Code,
Codex CLI, Cursor CLI, Devin CLI, Grok CLI, Kimi CLI, and OpenCode**, plus one generated **main
orchestrator** Skill (`kaola-project-runner`, display name **Project Runner**). A controlling
agent can start a session in a Git repository, send instructions, read replies and runtime
evidence, and stop that exact owned session. Communication uses structured ACP (Agent Client
Protocol) or a tmux terminal.

Use a worker Skill to delegate implementation, request a second review, or continue work in
another runtime. Use the main Skill when the host Agent should supervise explicitly authorized
CLI workers through those seven transport Skills. Pair either with
[Kaola Workflow](https://github.com/KaolaBrother/Kaola-Workflow) to give that work a recoverable
path from issue to verified delivery.

## Agent runtime support

There are two independent choices: **which agent loads the Skill**, and **which CLI it drives**.
For example, Claude Code can load the Codex Runner Skill to work through Codex CLI.

### Target CLIs

Each target has its own generated **worker** Skill, platform manifest, and launch adapter.
The main orchestrator Skill is generated separately and is not an eighth platform.

| Target runtime | Skill | CLI executable | Default transport |
|---|---|---|---|
| Claude Code | `claude-code-kaola-project-runner` | `claude` | PTY |
| Codex CLI | `codex-kaola-project-runner` | `codex` | ACP |
| Cursor CLI | `cursor-cli-kaola-project-runner` | `cursor-agent` | ACP |
| Devin CLI | `devin-kaola-project-runner` | `devin` | ACP |
| Grok CLI | `grok-kaola-project-runner` | `grok` | ACP |
| Kimi CLI | `kimi-cli-kaola-project-runner` | `kimi` | ACP |
| OpenCode | `opencode-kaola-project-runner` | `opencode` | ACP |

ACP returns structured replies and events. PTY preserves the native terminal UI, including
terminal-only login and selection flows. Choose explicitly with `--transport acp|pty`;
capabilities vary by platform. Claude's ACP wrapper remains experimental; PTY is its default.

### Main orchestrator Skill

`kaola-project-runner` (display name Project Runner) is a control-plane Skill for a host Agent
that already has explicit CLI authorization. It recovers live work, dispatches through the seven
worker Skills, reviews evidence before finalize, and keeps close-out ownership after a session
stops. Whenever open PRs exist, it favors advancing them through review, validation, accepted
finalize/merge, and cleanup, while other authorized work may continue in parallel. A blocked PR
keeps an owner and next action without becoming a global barrier. Completion stops leftover idle
owned sessions, including ACP; idle is not keep-alive. Ending a run defaults to finishing in-hand
issues and a clean workspace. A stated stop boundary blocks new tasks and new issues without
dropping in-hand work. Only an explicit "stop here, continue later" pauses that cleanup and
preserves recovery. It does not add a platform manifest, transport adapter, scheduler, PR queue, or
backlog mirror. Heartbeat and completion policy live here; worker Skills stay transport-only.
`templates/grok-golden/` remains frozen historical evidence, not this Skill's contract.

### Agents that load the Skills

The installer provides native skill-directory destinations for **Codex, Claude Code, Cursor,
and Devin**. Other hosts can use `--skills-dir /absolute/path` if they can load `SKILL.md` and
execute shell commands in an environment with the required tools.

These are portable Agent Skills, with no dependency on a Codex installation. This does not mean
every host/target combination has been tested. Recorded end-to-end host coverage includes Codex
and Devin; see [validation and evidence](#validation-and-evidence) for the limits.

## What Runner does

- Start, inspect, and stop an exact session associated with a repository and target CLI.
- Send agent-selected prompts; transfer native keys through PTY where supported.
- Return replies, tool events, terminal output, process facts, and transport receipts.
- Apply per-run model and effort choices, with platform presets and explicit overrides.
- Resume native conversations where supported, or let the agent choose a fresh session.
- Expose ACP sessions for human inspection through `list`, `view`, and `follow`.

The controlling agent chooses the task, interprets the output, and decides what to do next.
Runner reports runtime and model observations as evidence. A successful send or a finished reply
alone does not establish that the task is complete. Worker Skills do not automatically retry
prompts, switch transports, upgrade models, or schedule recurring work. Project-level heartbeat
and acceptance belong to the main orchestrator Skill when that Skill is in use.

## Collaborative delivery with Kaola Workflow

[**Kaola Workflow**](https://github.com/KaolaBrother/Kaola-Workflow) provides the engineering
workflow: issue claims, a recoverable Mission List, validation, finalization, and delivery records.
Runner provides the communication channel through which an agent asks another runtime to do that
work. Both can be used independently.

```text
Host Agent
  └─ Main Skill kaola-project-runner (optional control plane)
        └─ Worker Runner Skill → ACP or PTY → Target CLI
                                              └─ Kaola Workflow
                                                  Issue → Claim → Mission List → Work & validation
                                                        → Finalize → Archive & sink
```

A typical collaboration works like this:

1. Install Runner for the controlling agent and
   [install Kaola Workflow](https://github.com/KaolaBrother/Kaola-Workflow/blob/main/docs/installation.md)
   for the target runtime. Workflow must be available to the CLI doing the work.
2. The controlling agent selects a target CLI and opens an owned session in the project repository.
3. It sends the task and asks the CLI to start or resume with `workflow-next`, following that
   runtime's installed Workflow instructions.
4. The CLI claims the issue, records the Mission List, performs the work, and validates the result.
   The controlling agent reads replies and work evidence, then sends follow-up instructions as needed.
5. The agent supervises `kaola-workflow-finalize` and verifies the selected PR or merge/sync outcome,
   archive, and sink. It stops the owned Runner session when further interaction is no longer needed.

This combination gives you:

- **Cross-runtime collaboration:** choose an appropriate CLI while keeping the task's engineering
  process consistent. Each CLI retains its own tools, model options, and native behavior.
- **Recoverable work:** Workflow's claim, Mission List, and results let an agent reconcile progress
  after an interruption. Runner can reconnect to a supported native conversation or start another
  session that reads those records; recovery remains an agent decision.
- **Verifiable handoffs:** replies show what the CLI says; repository changes, validation evidence,
  and forge state establish what it delivered. A delivered PR is distinct from a merged change.

All seven worker Skills include this optional Workflow guidance. Starting a worker Skill alone does
not install Workflow, claim an issue, send `workflow-next`, or create a heartbeat. The main
orchestrator Skill may register a host heartbeat after an authorized CLI allowlist exists. Runtime
coverage is also independent: Workflow's support for a runtime does not imply a Runner adapter
exists for it.

Example instruction to an agent with the Claude Code Runner Skill loaded:

> Use Claude Code to work on issue #42 in this repository. If Kaola Workflow is available there,
> follow its workflow-next instructions, inspect the implementation and validation evidence, and
> supervise workflow finalization through PR delivery. Stop the owned session when finished.

## Install

Requirements: Bash, Python 3, tmux, Git, and the selected target CLI with working authentication.
ACP wrappers may also require Node.js/npx; exact commands are in the [platform manifests](platforms/).
Runner does not install the target CLIs or provide model access.

```bash
git clone https://github.com/KaolaBrother/kaola-project-runner.git
cd kaola-project-runner
./scripts/render-skills.py --check
./scripts/install-local.sh
```

The default installs all seven worker Skills plus the main orchestrator Skill into
`${CODEX_HOME:-$HOME/.codex}/skills` as standalone copies. Use `--method link` to symlink
Skills to this checkout for Project Runner development. Select another host, a worker
subset, or skip the orchestrator:

```bash
# Install all worker Skills plus the orchestrator for Claude Code, Cursor, or Devin.
./scripts/install-local.sh --runtime claude-code
./scripts/install-local.sh --runtime cursor
./scripts/install-local.sh --runtime devin

# Let Claude Code drive only Codex CLI and OpenCode; still install the orchestrator.
./scripts/install-local.sh --runtime claude-code --platform codex,opencode

# Workers only (no main Skill).
./scripts/install-local.sh --runtime cursor --no-orchestrator

# Explicit destination; copy is the default, so --method copy is optional.
./scripts/install-local.sh --skills-dir "$PWD/.agent/skills"

# Maintainer development: symlink Skills to this checkout.
./scripts/install-local.sh --method link
```

`--runtime` selects the host's skill directory; `--platform` selects worker CLI Skills only.
`--no-orchestrator` skips `kaola-project-runner`. That name is not a `--platform` id.
`--runtime` and `--skills-dir` are mutually exclusive. Copies work without this checkout;
`--method link` requires it to remain in place. Reinstalling the default over an owned
source link migrates that Skill to a copy. The installer preserves foreign files and
modified copies.

Use the host's Skill discovery mechanism, or have the agent read the installed `SKILL.md` directly.
In Codex, a Skill can be invoked as `$claude-code-kaola-project-runner`, for example.

To uninstall, repeat the same destination and worker selection with `--uninstall`. Add
`--no-orchestrator` to leave the main Skill in place. Optional `kaola-acp` helper links in
`~/.local/bin` are installed by default only for the Codex destination. Use `--bin-links`
elsewhere; removing those links requires `--uninstall --bin-links`.
See the [installer reference](docs/api.md#installer) for all options.

## Direct command example

From this checkout, the shared entry point accepts a platform, operation, repository, and session:

```bash
REPO="/absolute/path/to/your/git-repository"
SESSION="opencode-example"

./scripts/kaola-tmux.sh opencode preflight --repo "$REPO" --session "$SESSION"
./scripts/kaola-tmux.sh opencode start --repo "$REPO" --session "$SESSION"
./scripts/kaola-tmux.sh opencode send --repo "$REPO" --session "$SESSION" \
  --text 'Explain this repository and summarize its test commands.'
./scripts/kaola-tmux.sh opencode observe --repo "$REPO" --session "$SESSION"
./scripts/kaola-tmux.sh opencode capture --repo "$REPO" --session "$SESSION"

# Read the reply and decide whether more interaction is needed before stopping.
./scripts/kaola-tmux.sh opencode stop --repo "$REPO" --session "$SESSION"
./scripts/kaola-tmux.sh opencode status --repo "$REPO" --session "$SESSION"
```

Installed Skills use their own `scripts/runtime-tmux.sh` with the same operations and no platform
argument. Invoke it by absolute path; `--repo` identifies the project being worked on.

Model selection uses `--tier default|upgrade` or an explicit `--model ID` with optional
`--effort LEVEL`. Presets live in the [platform manifests](platforms/); Fast is off unless requested.
Resume with `start --resume NATIVE_SESSION_ID` or `start --continue` where the runtime supports it.

**Permission defaults matter:** launches generally request the platform's broad automatic-approval
mode. OpenCode's default ACP path has no skip-permission launch flag. Use `--permission-mode` where
supported and check the native semantics: Codex ACP's `read-only` mode can write workspace files;
strict Codex read-only execution requires `--transport pty --permission-mode read-only`.
Authentication and workspace trust remain native CLI concerns.

For ACP session watching, use `kaola-acp list`, `kaola-acp PLATFORM view`, or
`kaola-acp PLATFORM follow` with the relevant repository and session arguments. Full transport,
permission, key, recovery, and receipt details are in the [command reference](docs/api.md) and
[ACP watch guide](docs/acp-watch/README.md).

## Validation and evidence

```bash
./scripts/render-skills.py --check
./scripts/validate.sh
```

The offline suite checks generated Skills, installer behavior, shell syntax, transport contracts,
and regression cases in an isolated temporary home directory. Live validation separately exercises
start, read, send, read-back, and exact-session stop with the actual CLI and account.

Published evidence includes [PTY communication tests](docs/live-smoke-issue-9-2026-08-31.md),
[Grok and Kimi ACP experiments](docs/poc-acp-transport-2026-09-11.md), and
[Cursor, Devin, and OpenCode ACP verification](docs/acp-live-verification-2026-09-11.md).
These are dated results, not a guarantee for every CLI version, model, or account. The recorded
Claude tests establish prompt transport and login-error read-back, not authenticated model
execution; its ACP wrapper failed initialization in the published September 11 run.

## Development

Edit the shared [worker Skill template](templates/SKILL.md.tmpl),
[orchestrator templates](templates/orchestrator/), [platform manifests](platforms/), or
[adapters](scripts/adapters/), then run `./scripts/render-skills.py --write` and validate. Commit the
generated `skills/` output; do not edit it by hand. `templates/grok-golden/` is frozen historical
compatibility evidence, not the main orchestrator contract.

See [architecture](docs/architecture.md), [development conventions](docs/conventions.md), and
[the changelog](CHANGELOG.md).

## License and use

This project is **source-available**, not licensed under an OSI-approved open-source license.
You may view, run, and modify it for personal learning, research, evaluation, and other
non-commercial purposes.

Commercial use of this project or derivative works requires prior written permission from the
copyright holder. This includes sales, paid services, SaaS, commercial product integration, and
paid products or services built around the project. Contact the repository owner for commercial
licensing.

All rights outside this limited permission are reserved. The project is provided "as is", without
express or implied warranties.
