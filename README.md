# Kaola Project Runner

**Let one agent work through another agent's CLI.**

One controlling agent can coordinate multiple projects at once. With Kaola-Delegator,
each project gets its own delegated Host running one Project Runner Agent; that Runner
assigns the project's authorized workers to separate issues. Each worker can use
Kaola Workflow to autonomously advance its issue, verify the result, and report back.
Project records and worktrees stay within that project's canonical repository; workers
and authorization are not pooled across projects.

This repository provides:

- ten self-contained **worker** Agent Skills — Claude Code, Codex CLI, Cursor CLI,
  Devin CLI, Grok CLI, Kimi CLI, OpenCode, ZCode, Droid CLI, and dsh (DeepSeek
  Harness). A controlling agent starts a session in a Git repository, sends
  instructions, reads replies and runtime evidence, and stops that exact owned
  session. Communication uses structured ACP (Agent Client Protocol) only.
- the main control-plane Skill **Project Runner** (`kaola-project-runner`): recover
  authorization, plan, dispatch, heartbeat, accept before finalize, own close-out.
- the external **Kaola-Delegator** Skill (`kaola-delegator`) for hands-off delegation
  from an outer Agent.

Pair a chosen entry with
[Kaola Workflow](https://github.com/KaolaBrother/Kaola-Workflow) when that work needs
a recoverable path from issue to verified delivery.

## Contents

1. [Choose an entry](#choose-an-entry) — Delegator / Project Runner / Platform Runner / Workflow Next
2. [Kaola Workflow integration](#kaola-workflow-integration) — normal path, orchestrator binding, evidence-backed exception
3. [Install and begin](#install-and-begin)
4. [Select workers](#select-workers) — [runtimes](#runtimes), [model selection](#model-selection), [worker classes](#worker-classes) (Expert / Worker / Elite), [preset catalog](#preset-catalog) (all 10 runtimes, 21 presets), [platform notes](#platform-notes)
5. [Authorization](#authorization) — [authorization by class](#authorization-by-class), [choosing a worker](#choosing-a-worker), [seat binding and switching](#seat-binding-and-switching), [authorization before a new Host](#authorization-before-a-new-host)
6. [What you specify and what agents own](#what-you-specify-and-what-agents-own)
7. [Daily use](#daily-use) — session commands, steering, watching ACP sessions
8. [For agents](#for-agents)
9. [Further documentation](#further-documentation) · [Development](#development) · [License and use](#license-and-use)

## Choose an entry

Pick the most direct entry for how much you want to control. Do not force every task
through every layer. Each layer finishes its own job and does not repeat the next.

| If you want | Use | What it does | What it does not do |
|---|---|---|---|
| Hands-off: delegate the whole project | **Kaola-Delegator** (`kaola-delegator`) | Extract goal, progress, authorized platforms/quota/priority, and stop boundary; start or resume **one** delegated Host that must load Project Runner; relay evidence-based pacing feedback at its agreed cadence | Dispatch workers, copy a mission ledger, maintain the inner heartbeat, or bind per-worker variables |
| Control the orchestration | **Project Runner** (`kaola-project-runner`) | Recover authorization, plan, dispatch, heartbeat, accept before finalize, and own close-out | Run as a second orchestrator on the same project |
| Coordinate one or a few issues yourself | **Platform Runner** (`<platform>-kaola-project-runner`) | Exact-session start, send, read, and stop | Task planning or completion judgment |
| Do one issue in this Agent | **Workflow Next** | Claim or resume that issue and advance it | Finalize, archive, and sink — those are Workflow finalize |

Delegation is the **hands-off** path, not a mandatory chain: you can instead load
Project Runner directly for one project's orchestration, use a Platform Runner to
coordinate one or a few issues yourself, or use Workflow Next in the current Agent for
one issue. A worker's result returns to its project's Runner for review and close-out;
the outer Agent supervises the project-level delegation, not each inner worker.

**One project, one Project Runner Agent.** Several workers on one project are not
several orchestrators, and several issues are not a bundle. Start and stop use the
bound canonical project root and an exact session. Do not add a registry, lock, or
second scheduler.

**Status.** Kaola-Delegator is included in this repository and the v0.4.0 release;
installation on a consuming machine and Grok Bot account-side live UAT still require
separate verification. The delegated Host can be any of the ten CLI platforms, chosen
apart from the authorized worker platforms. Grok Bot is a bridge host for
Kaola-Delegator only — not a worker platform and not a Project Runner host; see
[Grok Bot host](docs/grok-bot-host.md).

## Kaola Workflow integration

[**Kaola Workflow**](https://github.com/KaolaBrother/Kaola-Workflow) provides the
engineering workflow: issue claims, a recoverable mission ledger, validation,
finalization, and delivery records. Runner provides the communication channel through
which an agent asks another runtime to do that work. Both can be used independently.

1. Install Runner for the controlling agent and
   [install Kaola Workflow](https://github.com/KaolaBrother/Kaola-Workflow/blob/main/docs/installation.md)
   for the target runtime. Workflow must be available to the CLI doing the work.
2. Inspect current Git and Workflow evidence, then start an owned session with
   `--repo` bound to the consuming project's **canonical project root** (the main
   checkout, not a Workflow child worktree).
3. Send the task and ask that CLI's main conversation to start or resume with
   `workflow-next`, following that runtime's installed Workflow instructions. The
   worker's Workflow then creates, resumes, or recovers its own run, branch, mission
   ledger, and child worktree. One run claims one real issue; a second issue means a
   second run, session, and name.
4. The CLI performs the work and validates the result. The controlling agent reads
   replies and work evidence, then sends follow-up instructions as needed. Keep
   `kaola-workflow-finalize` in the worker conversation; the outer agent verifies
   evidence before directing it.
5. After acceptance, the agent supervises `kaola-workflow-finalize` and verifies the
   selected PR or merge/sync outcome, archive, and sink. It stops the owned Runner
   session when further interaction is no longer needed.

Several exact Runner sessions may share one canonical project root while their
Workflows own distinct child worktrees. Linked-worktree starts, outer-created
branches, and existing-run recovery are Agent decisions, not transport gates.

Example instruction to an agent with the Claude Code Runner Skill loaded:

> Use Claude Code to work on issue #42 in this repository. Start the owned session at
> the canonical project root. If Kaola Workflow is available there, follow its
> workflow-next instructions so that runtime owns the child worktree, inspect the
> implementation and validation evidence, and supervise workflow finalization through
> PR delivery. Stop the owned session when finished.

### Normal path

Start Claude Code with `--repo /path/to/project` at the canonical project root. Ask
that conversation to invoke `workflow-next` for issue #52. Workflow claims the issue
and creates or resumes its chosen child worktree. The Runner session remains the
root-started exact session.

### Orchestrator binding

A Project Runner Orchestrator states that root once instead of re-proving it on every
dispatch:

```bash
export KAOLA_PROJECT_RUNNER_CANONICAL_REPO=/path/to/project
```

While it is exported, `--repo` may be omitted and is completed from that root, and a
`start` that names a different root — a linked worktree of the same repository
included — is refused with `canonical-root-mismatch` and `mutation_performed: false`
before any process, holder, or record exists. Commands on a session that already
exists keep the `--repo` they were given, so earlier work stays observable and exactly
stoppable by its own locator. Without that export nothing changes.

### Evidence-backed exception

If a live run already exists and an earlier session was started inside a child
worktree, the controlling Agent may stop it and restart at the canonical project root,
or continue there for review or recovery. Report the chosen Git root. The transport
did not refuse the linked worktree: a session already running in a child worktree is
advisory — preserve work, inspect state, then continue, stop/restart at root, or use
another Workflow recovery path.

This combination gives you cross-runtime collaboration (choose the CLI while keeping
the engineering process), recoverable work (the claim, mission ledger, and results
reconcile after an interruption), and verifiable handoffs (replies show what the CLI
says; repository changes, validation evidence, and forge state establish what it
delivered). Starting a worker Skill alone does not install Workflow, claim an issue,
send `workflow-next`, or create a heartbeat. Runtime coverage is also independent:
Workflow's support for a runtime does not imply a Runner adapter exists for it.

## Install and begin

Requirements: Bash, Python 3, Git, and the selected target CLI with working
authentication. ACP wrappers may also require Node.js/npx; exact commands are in the
[platform manifests](platforms/). Runner does not install the target CLIs or provide
model access.

```bash
git clone https://github.com/KaolaBrother/kaola-project-runner.git
cd kaola-project-runner
./scripts/render-skills.py --check
./scripts/install-local.sh
```

`./scripts/install-local.sh` verifies Skill payloads. Exit 0 and a `verify:` line do not
finish installation. On the bound target, finish by following
[ACP layer preparation during install](docs/api.md#acp-layer-preparation-during-install):
survey each detected in-scope runtime once, then resolve, prepare, and verify the actual ACP
components, and report one compact row per runtime in that same result. `--runtime` is the
Skill destination, not the only CLI to inspect. A locator attestation is not this step.

The default installs all ten worker Skills plus the main orchestrator Skill into
`${CODEX_HOME:-$HOME/.codex}/skills` as standalone copies. `--runtime` selects the
host's skill directory, `--platform` selects worker CLI Skills only, and
`--no-orchestrator` skips `kaola-project-runner` (that name is not a `--platform`
id). `--runtime` and `--skills-dir` are mutually exclusive; copies work without this
checkout, while `--method link` symlinks Skills to it for development.

```bash
# Native host destinations (verified skill directories):
./scripts/install-local.sh --runtime claude-code   # ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills
./scripts/install-local.sh --runtime cursor       # $HOME/.cursor/skills
./scripts/install-local.sh --runtime devin        # ${DEVIN_CONFIG_DIR:-$HOME/.config/devin}/skills
./scripts/install-local.sh --runtime zcode        # $HOME/.zcode/skills
./scripts/install-local.sh --runtime grok-cli     # $HOME/.grok/skills
./scripts/install-local.sh --runtime droid        # $HOME/.agents/skills
./scripts/install-local.sh --runtime opencode     # $HOME/.config/opencode/skills
./scripts/install-local.sh --runtime kimi-cli     # $HOME/.agents/skills AND ${KIMI_CODE_HOME:-~/.kimi-code}/skills

# A ZCode workspace .zcode/skills or .agents/skills destination goes through --skills-dir:
./scripts/install-local.sh --skills-dir "$PWD/.zcode/skills"

# Let Claude Code drive only Codex CLI and OpenCode; still install the orchestrator.
./scripts/install-local.sh --runtime claude-code --platform codex,opencode

# Workers only (no main Skill).
./scripts/install-local.sh --runtime cursor --no-orchestrator

# Explicit destination; copy is the default, so --method copy is optional.
./scripts/install-local.sh --skills-dir "$PWD/.agent/skills"

# Maintainer development: symlink Skills to this checkout.
./scripts/install-local.sh --method link
```

On Codex and generic `--skills-dir` destinations, `kaola-delegator` is also installed
next to Project Runner, whatever `--platform` selects, because any selected worker
platform can be its one Host. The Codex destination additionally installs one
Runner-owned user-level `SessionStart(compact)` recovery entry in
`${CODEX_HOME:-$HOME/.codex}/hooks.json` whenever the control-plane Skills are in the
plan: Codex asks you to review and trust the new entry in `/hooks`, and it loads from
the next session — see [Codex host](docs/codex-host.md). `--skills-dir` never touches
a `hooks.json`.

Grok Bot has no installer destination. Save the thin bridge Skill
`hosts/grok-bot/kaola-delegator.md` on the account once, then register the
device-local locator on each execution target:

```bash
python3 scripts/kaola-locate.py register --target local --bin-dir <dir on PATH> --expect-revision <accepted commit>
kaola-project-runner-locate --target local --expect-revision <accepted commit>
```

The locator validates origin, revision, and a clean tree, and writes a bounded
attestation receipt beside the link. Registering it does not finish installation and does
not show that the execution target's runtimes are ACP-ready. Finish that bound target with
the same [ACP layer preparation during install](docs/api.md#acp-layer-preparation-during-install)
procedure. The one-write install, its fail-closed properties, and rollback are documented in
[Grok Bot host](docs/grok-bot-host.md).

Installed Skills are shared blocks counted by reference, so runtimes install and
uninstall independently; `kimi-cli` installs into both of its user roots, each with
its own receipt set. A reinstall restores a receipt-owned copy whose payload drifted;
edit repo templates and manifests, never installed copies. To uninstall, repeat the
same destination and worker selection with `--uninstall` (`--no-orchestrator` leaves
the main Skill in place). Optional `kaola-acp` helper links in `~/.local/bin` are
installed by default only for the Codex destination; use `--bin-links` elsewhere and
`--uninstall --bin-links` to remove them. See the
[installer reference](docs/api.md#installer) for all options.

The examples above are payload installs. Each one is finished only by the ACP procedure
linked from the default install.

Use the host's Skill discovery mechanism, or have the agent read the installed
`SKILL.md` directly. In Codex, a Skill can be invoked as
`$claude-code-kaola-project-runner`, for example.

## Select workers

There are two independent choices: **which agent loads the Skill**, and **which CLI
it drives**. For example, Claude Code can load the Codex Runner Skill to work through
Codex CLI.

### Runtimes

Each target has its own generated **worker** Skill, platform manifest, and launch
adapter. The main orchestrator Skill is generated separately and is not an eleventh
platform.

| Target runtime | Skill | CLI executable |
|---|---|---|
| Claude Code | `claude-code-kaola-project-runner` | `claude` |
| Codex CLI | `codex-kaola-project-runner` | `codex` |
| Cursor CLI | `cursor-cli-kaola-project-runner` | `cursor-agent` |
| Devin CLI | `devin-kaola-project-runner` | `devin` |
| Grok CLI | `grok-kaola-project-runner` | `grok` |
| Kimi CLI | `kimi-cli-kaola-project-runner` | `kimi` |
| OpenCode | `opencode-kaola-project-runner` | `opencode` |
| ZCode | `zcode-kaola-project-runner` | explicit `KAOLA_ZCODE_ENTRY` + `KAOLA_ZCODE_NODE` |
| Droid CLI | `droid-kaola-project-runner` | `droid` |
| dsh (DeepSeek Harness) | `dsh-kaola-project-runner` | `dsh` |

Every platform communicates over ACP only, with structured replies and events;
capabilities vary by platform. Login is a human act in a native terminal, outside the
Runner.

### Model selection

Model selection uses `--tier NAME` or an explicit `--model ID` with optional
`--effort LEVEL` (an explicit model or effort wins over the preset). Only `default`
is common to every platform and applies when `--tier` is omitted. Every other name is
that platform's own model or purpose word, with no universal ranking, alias, or
"upgrade" between them; effort is a separate parameter, not a universal quality tier,
so Claude Code's `opus-xhigh` preset or the `max` on Luna does not make either an upgrade. A name the platform
does not declare (including the retired `upgrade`) is a typed `tier-not-declared`
refusal, never a quiet fallback to `default`. Presets live in the
[platform manifests](platforms/); Fast is off unless requested. Resume with
`start --resume NATIVE_SESSION_ID` or `start --continue` where the runtime supports
it.

### Worker classes

Every runtime/preset belongs to one of three owner-defined operating classes. The
class attaches to the **preset**, not the whole runtime: Claude Code, for example, has
Elite presets `claude-code/default`, `claude-code/opus-xhigh`, and
`claude-code/sonnet`, and an Expert `claude-code/fable`. Classes are operating
roles, not benchmark claims, and they do not change which model a Host itself runs.

| Class | Presets | Role | Authorization |
|---|---|---|---|
| **Expert** | 3 | Complex thinking only: difficult analysis, design, objective decomposition, and review judgments. No concrete implementation or execution; not an ordinary worker seat. | Your explicit permission for **each** task or use. The Host judges completion and exact-stops the seat; another use needs fresh permission, while the same approved task continues across turns and recovery without asking again. |
| **Worker** | 5 | Cheaper and generally weaker; simpler, bounded work that adds parallel throughput. | Default-authorized: no per-seat, count, or priority approval, and outside the general worker cap. Real account/token/service limits and your explicit restrictions still apply. |
| **Elite** | 13 | The main execution workforce: primary implementation and demanding execution. | Your explicit runtime/preset/count grant, within its caps and seat-switch rules. A valid grant stays valid for its scope; no per-task permission. |

An Expert review informs the Host; it never replaces the Host's acceptance or its
ownership of the seat lifecycle.

### Preset catalog

Every row below is rendered directly from the [platform manifests](platforms/) — the
same rows as the generated
[profile-catalog.md](skills/kaola-project-runner/references/profile-catalog.md)
reference — grouped by class. Each row's **Preset ID** `<platform>/<tier>` is its one
stable ID: grants, seat snapshots, and authorization relays name a preset by that
exact ID (so `cursor-cli/default` and `grok/default`, or `claude-code/default`,
`claude-code/opus-xhigh`, and `claude-code/sonnet`, never blur), with the model name and parameters on the same
row. The ID names a configured preset, not proof of the actually-running model.
`claude-code/default` and `claude-code/opus-xhigh` both launch the native model
alias `opus` at different efforts; the preset ID is not that alias. Each
profile line is user-defined selection guidance,
not a measured capability; it never changes the preset's model, effort, or Fast and
never gates `start`. Devin applies each preset through its launch `--model`; both
named Devin presets are SWE-2-sidekick fusions. Droid's `-fast` catalog IDs are
explicit `--model` choices, not a separate Fast toggle.

<!-- KW-README-PRESETS-START -->
| Class | Runtime | `--tier` | Preset ID | Model | Effort / parameters | Profile |
|---|---|---|---|---|---|---|
| Elite | Claude Code | `default` | `claude-code/default` | Opus 5.5 | effort=high | All-round execution worker, especially strong at complex execution work and UI and 3D visual implementation. |
| Elite | Claude Code | `opus-xhigh` | `claude-code/opus-xhigh` | Opus 5.5 | effort=xhigh | Plans, designs, and reviews difficult, complex work and handles deep reasoning tasks, with particular strength in UI and 3D visual design and review; does not perform implementation. |
| Elite | Claude Code | `sonnet` | `claude-code/sonnet` | Sonnet | effort=high | All-round execution worker, well suited to well-scoped work, especially UI and 3D visual implementation. |
| Elite | Codex CLI | `default` | `codex/default` | GPT-6.1 Sol | effort=high | All-round execution worker, strong at exploring directions, finding problems, and review; good at UI and 3D visual work, with computer-use capability. |
| Elite | Cursor CLI | `default` | `cursor-cli/default` | Grok 4.7 | effort=xhigh (encoded in model ID), fast=false | Investigates unfamiliar problems, explores solution paths, and autonomously carries them through implementation; well suited to long-running, adaptive work. |
| Elite | Cursor CLI | `opus` | `cursor-cli/opus` | Claude Opus 5.5 | effort=high (encoded in model ID) | All-round execution worker, especially strong at complex execution work and UI and 3D visual implementation. |
| Elite | Devin CLI | `opus-fusion` | `devin/opus-fusion` | Opus Fusion | effort=high (encoded in model ID) | All-round execution worker, especially strong at complex execution work. |
| Elite | Droid | `default` | `droid/default` | Auto Model | no Runner effort override | All-round worker, balanced in every respect, suited to many kinds of tasks. |
| Elite | Droid | `opus` | `droid/opus` | Opus 5.5 | reasoning_effort=high | All-round execution worker, especially strong at complex execution work and UI and 3D visual implementation. |
| Elite | Droid | `core` | `droid/core` | Kimi K3 | reasoning_effort=max | Strong at visual design and visual inspection, with good UI and design taste. |
| Elite | Grok CLI | `default` | `grok/default` | Grok 4.7 | effort=xhigh, fast=false | Suits exploratory, long-running autonomous work; give clear stage goals and exit conditions. |
| Elite | Kimi CLI | `default` | `kimi-cli/default` | Kimi K3 | thinking=max | Strong at visual design and visual inspection, with good UI and design taste. |
| Elite | Kimi CLI | `kimi-k2-8` | `kimi-cli/kimi-k2-8` | Kimi K2.8 | thinking=max | All-round implementation worker for every kind of hands-on development and implementation task. |
| Worker | Codex CLI | `luna` | `codex/luna` | GPT-6 Luna | effort=max | Fast, flexible implementation worker with good reasoning for its class and computer-use capability; relatively exploratory and suited to tasks whose implementation path is not fully predetermined. |
| Worker | Devin CLI | `default` | `devin/default` | SWE-2 | effort=max (encoded in model ID) | Capable full-cycle engineering worker. |
| Worker | dsh | `default` | `dsh/default` | DeepSeek V4.1 Flash | no Runner effort override | Fast implementation worker for tasks with clear goals and boundaries; emphasizes autonomous progress, iterative validation, and self-repair. |
| Worker | OpenCode | `default` | `opencode/default` | DeepSeek V4.1 Flash | no Runner effort override | Fast implementation worker for tasks with clear goals and boundaries; tends to investigate deeper root causes and reduce unrelated changes. |
| Worker | ZCode | `default` | `zcode/default` | GLM 5.3 | thought=max | Autonomous engineering worker inclined to investigate, make decisions, iterate through failures, and carry substantial tasks toward completion with less hand-holding. |
| Expert | Claude Code | `fable` | `claude-code/fable` | Fable | effort=high | Design, goal definition and decomposition, issue creation, and review; only with explicit user permission for each task; no concrete implementation or execution, not a regular worker. |
| Expert | Codex CLI | `astra` | `codex/astra` | GPT-6 Astra | effort=high | Design, goal definition and decomposition, issue creation, and review; only with explicit user permission for each task; no concrete implementation or execution, not a regular worker. |
| Expert | Devin CLI | `fable` | `devin/fable` | Fable Fusion | effort=high (encoded in model ID) | Non-visual design, goal definition and decomposition, issue creation, and review; not strong at UI or other visual design. Only with explicit user permission for each task; no concrete implementation or execution, not a regular worker. |
<!-- KW-README-PRESETS-END -->

This is the full supported-runtime catalog, not a machine-local choice list.
Local choices require a runtime discovered in the bound execution target's
effective launch context and a matching installed platform Runner that declares
the tier. Show each discovered runtime with its Class and current authorization.
Routine context keeps a capability summary of present profiles, not one
profile row per preset. At a dispatch decision the Host projects eligible
candidates and does not load the full table. The README stays the full
catalog on every machine.
See [choosing a worker](#choosing-a-worker).

### Platform notes

Concise caveats to know before the first dispatch. Per-platform launch commands,
environment, quirks, and verification status are in each
[platform manifest](platforms/) and each worker Skill's `references/platform.md`
and `references/acp.md`; transport and bridge internals are in the
[architecture notes](docs/architecture.md).

- **dsh** runs its shipped automation-only ACP profile (`dsh --profile acp`); it
  needs no login and has no terminal UI, and the profile must already exist under
  `$DSH_HOME`. It starts with **full access by default** (`danger-full-access`, no
  sandbox, approval `never`) — set the launch variable `DSH_PERMISSION_MODE` or pass
  `--mode` (`read-only`, `workspace-write`, `danger-full-access`) for anything else.
  The shipped profile also pins the `deepseek-official` route, so a session can
  report `ready` and still fail its first prompt without an API key: supply
  `DEEPSEEK_API_KEY` or pass `--model` to select a credentialed route.
- **Droid** defaults to Auto Model and **full bypass**; its `--permission-mode`
  values map to ACP autonomy levels ([command reference](docs/api.md)).
- **Claude Code** runs through a pinned ACP bridge shipped inside its worker Skill,
  under your claude.ai subscription and native Settings.
- **ZCode** needs an explicit absolute `KAOLA_ZCODE_ENTRY` plus `KAOLA_ZCODE_NODE`,
  and login happens in the ZCode desktop App.

## Authorization

Workers run only under authorization, and what you authorize depends on the
[class](#worker-classes) of the preset.

### Authorization by class

- **Worker presets** — the five Worker rows of the catalog — need nothing more than an
  authorized project task: no per-seat or per-preset approval and no priority order.
  Their live seats neither count toward nor are limited by the general worker
  concurrency cap. Membership is exactly those five rows; `claude-code/sonnet` is
  Elite and is not a member. Being a runtime's `default`
  preset does not make a preset a Worker. Actual account/token/service and resource
  limits still apply (an unspecified quota is not unlimited), and any explicit owner
  restriction wins.
- **Elite presets** need your explicit grant naming the runtime/preset and count.
  `claude-code/sonnet` uses that same grant: no default seat and no preset-specific
  cap, and this move does not raise the general worker cap. `claude-code/opus-xhigh`
  is the thinking-only Opus preset. Moving that role off `claude-code/default` does
  not grant `claude-code/default` and does not add a seat. Grants you already gave
  stay valid within their scope. The authorized count is a
  hard cap on live worker processes, ACP holders included: stop-before-start at the
  cap, and an accepted seat keeps only the finalize/cleanup duties it owns until it
  owns none or is abandoned, when it is exact-stopped; give a new task a new
  session; idle is not keep-alive.
- **Expert presets** need your explicit permission for each task or use. When that
  task is complete the Host reclaims (exact-stops) the seat; the completed permission
  does not carry over to another task. Continuing or recovering the same approved
  task does not ask again.

### Choosing a worker

The Host decides in this order: **current authorization → class responsibility →
individual profile/task fit → available capacity and real resource limits.** Experts
contribute complex thinking only when you permitted that task; Elite presets carry
primary and demanding execution. `claude-code/default` is the Opus execution
preset at effort high, including when Claude Code is the Host and no tier was chosen, and
it implements. `claude-code/opus-xhigh` does not perform implementation.
A Claude Code Host still plans, dispatches, and accepts.
Worker presets take simpler, bounded work. A
listed capability never bypasses a missing Expert or Elite authorization — the Host
asks for it through the normal route when it genuinely needs it. Independent work
runs in parallel while real dependencies and write ownership are preserved. There is
no numerical ranking, complexity classifier, routing engine, fixed QA seat, forced
equal distribution across runtimes, or invented work to fill capacity. Worker
profiles keep their individual strengths — the GLM and SWE-2 presets carry
substantial, full-cycle tasks.

The Host keeps short class meanings and a capability summary of presets that
are both local and currently authorized: discovered Worker pool members (minus
your restrictions), granted Elite presets with their limits, and an Expert
preset only while its permitted task is active. A local preset requires a
runtime discovered in the bound target's effective launch context and a
matching installed platform Runner. Unknown discovery stays in the candidate
projection and is not described as absent or as a capability. At a dispatch
decision the Host reads that projection instead of a profile row per preset.
Kaola-Delegator relays grants and bound-target runtime/preset facts, not the
catalog. No separate profile registry or permission service exists.
### Seat binding and switching

A seat keeps its bound platform and preset; general dispatch authorization is not a
switch grant. Only your explicit grant for a particular seat lets the Host select or
switch that seat's model/preset, within the scope you allowed and the same agent
runtime, without asking again for each switch under that grant. Never switch across
runtimes. The same seat switches only when idle, through the existing
`drain-restart --resume ID` (or `--continue`) with an explicit `--tier`/`--model`: an
exact stop and resume, not a live hot switch (a busy seat refuses `drain-not-idle`).
A new standard-named seat is a new seat, not a switch of this one; no new flow. A
switch grant never authorizes an Expert use. Grants are recorded with the other
authorization in the consuming project's run records.

Ending a run defaults to finishing in-hand issues and a clean workspace. A stated
stop boundary blocks new tasks and new issues without dropping in-hand work; only an
explicit "stop here, continue later" pauses that cleanup and preserves recovery.

### Quota exhaustion

Recovery acts only on confirmed exhaustion — an explicit runtime/provider error or usage
fact that the relevant quota is exhausted. A generic 429, timeout, transient failure, or
reset-window metadata alone is reported, not acted on, and another runtime is not fresh
quota when evidence shows it shares the exhausted pool. By class:
an exhausted **Host** is replaced by Kaola-Delegator with one ZCode Host through the
existing exact-stop/new-Host handoff (if the Host is already ZCode, or that fallback
cannot operate, the Delegator asks you); an **Expert** task waits for your direction; an
exhausted **Elite** seat is reclaimed and loses its grant for this run — its task goes to
another already-authorized Elite, and only you reauthorize it; a **Worker** task moves to
another suitable Worker preset without cycling seats of an exhausted shared pool. With no
suitable authorized replacement, the task is reported and you are asked.

### Login or account access failure

An explicit `login expired`, `authentication required`, revoked or invalid credentials,
`account disabled`, or equivalent refusal pauses only the affected seat: its task,
locator, valid output, and exact identity are preserved, it gets no new work, it is
exact-stopped once the failed turn settles and marked temporarily paused in the run's
snapshot — a pause, not a grant revocation — and the runtime's exact message and the
seat go to you for account repair or direction, with unrelated work continuing. For the
Host itself the Delegator preserves the frontier and in-flight worker ownership and makes
no automatic Host switch. Neither the Delegator nor the Host ever attempts, retries, or
delegates login, re-login, credential refresh, or account switching for any cause, and
never asks you to paste secrets into chat; a paused seat resumes only after you confirm
access is restored and direct continuation.

A session that is still connecting, and a bare 429, timeout, or network error with no
explicit limiting reason, is neither: the cause stays unknown and is observed rather than
labeled quota or authentication.

### Authorization before a new Host

If a live delegated Host is confirmed stopped and its native resume id cannot restore
it, start a new standard-named Host as a new ACP session only after current
authorization is complete (goal, remaining work, platforms/members,
counts/concurrency, quota, priority, delivery/stop boundary; the five Worker
presets need no per-seat entries). Missing key values: ask,
do not `start`, do not guess a stale quota. Quota travels in the units the user
actually gave: a unit the user never gave is carried as unspecified and does not
block the start, not as unlimited and not as a fourth question; a unit whose meaning
is unclear is ambiguous, so ask.

Changing the outer Agent does not stop a live Host or re-claim issues: a successor
recovers the same live Host from the canonical Git root, the standard Runner session
name, and existing Runner `status`/receipts. Holder identity, sweep, and recovery
procedures are in the installed [kaola-delegator](skills/kaola-delegator/SKILL.md)
and [kaola-project-runner](skills/kaola-project-runner/SKILL.md) Skills and the
[documentation index](docs/README.md) — not on this page.

## What you specify and what agents own

| You (the user) specify | The agents own |
|---|---|
| The goal, the project, and the stop boundary | Choosing prompts, keys, and native tools; interpreting replies |
| Authorized platforms, worker count/concurrency, quota, priority | Exact-session transport: start, send, read, stop |
| Elite grants, per-task permission for any Expert use, and per-seat switch grants | Evidence-first review, acceptance before finalize, close-out |
| When to finalize, archive, or stop | Semantic completion judgments; never auto-retry, model upgrades, or scheduling |

Runner reports runtime and model observations as evidence. A successful send or a
finished reply alone does not establish that the task is complete. Worker Skills do
not automatically retry prompts, upgrade models, or schedule recurring work.
Project-level heartbeat and acceptance belong to the main orchestrator Skill when
that Skill is in use; acceptance there separates testing (running checks) from QA
(judging evidence sufficiency and verification proportionality — see
`references/qa-evidence.md` in the installed `kaola-project-runner`). That Host is
the one owner of adaptive QA and documentation-accuracy coverage: it decides what
evidence is needed and when project-level checks run from actual change scope,
risk, integration state, and your delivery boundary — no fixed interval, issue
count, or extra QA seat. Accepting one issue's delivery is not a claim that
project QA is complete; aggregate checks not yet run stay pending in the Host's
existing records until their delivery point, and related issues may share one
bounded integration check. Kaola-Workflow owns claims, run recovery, delivery,
merge, closure, archive, and cleanup; a successful finalize or documentation
docking is a lifecycle fact, not a QA PASS. Required project checks stay required.

**Permission defaults matter:** the default is per platform, not one guarantee
across all ten. Claude Code, Codex, Devin, Droid, Kimi and ZCode apply an
advertised ACP skip-all option at start (`mode`, or `autonomy_level` for Droid).
Cursor and Grok carry only a launch flag (`--yolo`, `--always-approve`) and
advertise no ACP option; OpenCode's default ACP path has none at all. On a platform
with no verified ACP skip-all, a permission request may still arise: it surfaces as
a `permission_required` event and is settled with `permit` (delivery and wake
semantics in the [command reference](docs/api.md)). Use `--permission-mode` where
supported and check the native semantics — Codex ACP's `read-only` mode (codex-acp
2.0.0) is the upstream read-only sandbox, and a write needs an explicit client
approval. `workspace-write` is the preset that edits workspace files without a prompt.
Droid defaults to full bypass; its `--permission-mode` values
map to ACP autonomy levels. dsh's launch-variable default is in
[platform notes](#platform-notes). Authentication and workspace trust remain
native CLI concerns; per-platform facts are in each worker Skill's
`references/acp.md` and the [command reference](docs/api.md).

## Daily use

### Session commands

From this checkout, the shared entry point accepts a platform, operation, repository,
and session:

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

Installed Skills use their own `scripts/runtime-tmux.sh` with the same operations and
no platform argument. Invoke it by absolute path; `--repo` identifies the project
being worked on.

### Steering a running turn

`steer` delivers one Agent-chosen message to a turn that is **already running**,
alongside `send`. It is an ACP-only tool, and the Agent picks the mode. Which
platforms have a native mid-turn entry is read from `native_steering` in
`platforms/<id>.yaml` — `supported` means the entry exists, `unsupported` means it
was investigated and does not, and `unknown` means no probe has settled it. No roster
is pinned here, because that answer changes as surfaces are investigated:

```bash
# Native mid-turn entry, on a platform whose manifest says native_steering: supported.
./scripts/kaola-tmux.sh codex steer --repo "$REPO" --session "$SESSION" \
  --text 'Stop the current approach and do X instead.'

# The composite works on every platform and is always chosen explicitly: interrupt the
# turn, then continue the same session.
./scripts/kaola-tmux.sh droid steer --repo "$REPO" --session "$SESSION" \
  --steer-mode interrupt --text 'Stop the current approach and do X instead.'
```

The composite cancels the running turn, confirms it actually stopped, and then sends
the text once as the next turn on the same ACP session, so the conversation keeps its
context — interrupted-then-continued, never injection. A platform with no native
entry refuses a bare `steer` with `steer-mode-required` rather than interrupting on
its own, and if a cancel is not confirmed nothing is sent at all. Receipts state
consumption exactly and never overstate it; the full outcome vocabulary is in the
[command reference](docs/api.md).

### Watching ACP sessions

For ACP session watching, use `kaola-acp list`, `kaola-acp PLATFORM view`, or
`kaola-acp PLATFORM follow` with the relevant repository and session arguments. To
learn which platform CLIs are installed on the host, including login-shell installs a
narrow-PATH app cannot see, use the read-only `kaola-acp survey`: it starts no agent,
session, or holder. To resolve a model to its quota package without spending a turn,
use `kaola-acp packages` and `kaola-acp model-package`; an id with no verified rule
is `unmapped`. Full transport, permission, key, recovery, and receipt details are in
the [command reference](docs/api.md) and [ACP watch guide](docs/acp-watch/README.md).

## For agents

The worker Skills start, inspect, and stop an exact session associated with a
repository and target CLI; send agent-selected prompts (`key escape` maps to ACP
cancel, and there is no native key, menu, or editor transfer); return replies, tool
events, terminal output, process facts, and transport receipts; apply per-run model
and effort choices, with platform presets and explicit overrides; resume native
conversations where supported, or start a fresh session; and expose ACP sessions for
human inspection through `list`, `view`, and `follow`. The controlling agent chooses
the task, interprets the output, and decides what to do next.

- **Dispatch/collect**: Project Runner's routine heartbeat carries a compact
  capability summary. At a dispatch decision the same entry projects eligible
  candidates and runs one adopted research, QA, or report item, or a bounded
  fan-out, through the existing platform Runners. An on-demand Sidekick may
  prepare that plan, synthesize evidence, or do explicitly scoped light work.
  The Host still adopts the plan, accepts the result, and exact-stops seats.
- **Skill names**: `<platform>-kaola-project-runner` for each of the ten runtimes,
  `kaola-project-runner` (display name Project Runner) as the control plane, and
  `kaola-delegator` (display name Kaola-Delegator) for external delegation.
- **Read the installed or [generated](skills/) `SKILL.md`** for each Skill's exact
  commands; each worker Skill carries `references/platform.md` (presets, launch,
  login) and `references/acp.md` (transport, permission, quirk facts).
- **Report complete terminal, process, holder, repository, Workflow, and forge
  facts.** Activity, editor, approval, decision, model, Git, Workflow, and snapshot
  observations never authorize or block an Agent-selected transport; ordinary live
  change is evidence, not staleness. Refuse only objective transport impossibility or
  ambiguous/foreign target identity.
- **Host coverage**: not every host/target combination has end-to-end coverage
  (recorded: Codex and Devin); treat others as unverified until run there — see
  [development](#development).
- The ten worker Skills include optional Workflow guidance.

## Further documentation

- [Documentation index](docs/README.md) — architecture, API and command reference,
  host guides (ZCode, Codex, Grok Bot), host-entry evidence, ACP watch surface,
  conventions, and decision records.
- [CHANGELOG](CHANGELOG.md) — user-visible changes for every release, including
  whether running seats must restart.
- [architecture](docs/architecture.md) · [conventions](docs/conventions.md) ·
  [installer and command reference](docs/api.md)

## Development

```bash
./scripts/render-skills.py --write   # regenerate skills/ and the README preset catalog
./scripts/render-skills.py --check
./scripts/validate.sh
```

Edit the shared [worker Skill template](templates/SKILL.md.tmpl), [orchestrator
templates](templates/orchestrator/), [platform manifests](platforms/), or
[adapters](scripts/adapters/), then run `--write` and validate. Commit the generated
`skills/` output; do not edit it by hand. The README preset catalog between its
`KW-README-PRESETS` markers is generated from the same manifests — rerun `--write`
after manifest changes. `templates/grok-golden/` is frozen historical compatibility
evidence, not the main orchestrator contract.

The offline suite checks generated Skills, installer behavior, shell syntax, transport
contracts, and regression cases in an isolated temporary home directory. The full
contract suite needs a dev machine with `tmux`, bash >= 4 (`mapfile`/`BASHPID`), and
Python >= 3.10; a missing prerequisite skips its affected rows with a named receipt.
Live validation separately exercises start, read, send, read-back, and exact-session
stop with the actual CLI and account; dated live-evidence documents are linked from
the [documentation index](docs/README.md) and are dated results, not a guarantee for
every CLI version, model, or account.

## License and use

This project is **source-available**, not licensed under an OSI-approved open-source
license. You may view, run, and modify it for personal learning, research, evaluation,
and other non-commercial purposes.

Commercial use of this project or derivative works requires prior written permission
from the copyright holder. This includes sales, paid services, SaaS, commercial
product integration, and paid products or services built around the project. Contact
the repository owner for commercial licensing.

All rights outside this limited permission are reserved. The project is provided "as
is", without express or implied warranties.
