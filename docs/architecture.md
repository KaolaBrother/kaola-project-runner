# Architecture

## Product boundary

Kaola Project Runner is a runtime-neutral Agent Skills CLI communication driver: any agent that
can load a skill directory and run shell commands in an environment containing the target CLI can
use the same seven worker Skills, and Codex remains a fully supported consuming runtime. A separate
generated control-plane Skill, `kaola-project-runner` (display name Project Runner), supervises
explicitly authorized workers through those transport Skills. Worker Skills do not orchestrate
Kaola Workflow, implement Workflow, or own a runtime's configuration.

```text
Host Agent
    -> optional main Skill kaola-project-runner (heartbeat, dispatch, acceptance, close-out)
        -> communication-only worker Agent Skill
            -> manifest-selected transport
                -> ACP holder + structured protocol agent
                OR
                -> fixed platform adapter
                    -> exact owned tmux pane leader: managed relay
                        -> attested nested-PTY runtime child
            -> Agent-selected prompt, key, or optional Workflow command
```

The controlling Agent owns every command, orchestration, heartbeat, recovery, decision, and completion
choice. When the main Skill is in use, that Skill states how the host Agent recovers authorization,
dispatches workers, accepts work before finalize, stops leftover idle owned sessions (including ACP),
and defaults to finishing in-hand issues with a clean workspace close-out after a run.
The Runner owns exact-session control, evidence collection, prompt/key transfer, response
readback, and truthful mechanical receipts. Kaola Workflow owns lifecycle state only when the Agent
chooses to invoke it.

ACP Watch（见 `docs/acp-watch/` / issues #25–#27）：人类旁观订阅 holder 上的投影，不得成为第二条 agent stdio 客户端，也不得把原始 `session/update` 塞进 Skill 热路径。permit lock（#25）、`list`/`view`（#26）与本机 `follow`（#27）已实现。PTY 仍是登录与原生 TUI 接管。

Main-model choice is a per-run transport fact. A current-request `--model` wins; otherwise
`--tier default|upgrade` selects the manifest's declared preset (`default` when unset), resolved
against the current catalog. `--effort` applies only to the model selected in the same request, and
`--fast on` is an explicit per-run opt-in applied through the native mechanism (config option,
`-c service_tier`, `-fast` model variant, or process-scoped `--settings '{"fastMode": ...}'`) —
reported `unsupported` where none exists; where a mechanism exists the native CLI determines
model support and effective stays `unknown` without native evidence. The
selection enters the child as literal argv plus narrowly scoped invocation parameters, never by
rewriting global CLI configuration. `--resume`/`--continue` without selection flags preserves the
saved native session selection. There is no automatic escalation on complexity, failures, or elapsed
time; runtime-owned post-launch evidence is returned to the Agent and does not become permission to
use the communication channel.

## Grok golden contract

`templates/grok-golden/` is an immutable historical copy of the live-proven Grok Skill, metadata, lifecycle,
prompt, PR handoff, heartbeat, foreground scheduler, and closing references. Project prompt, task-mode,
scheduling, handoff, and lifecycle bytes. Those bytes remain frozen as reference evidence; active
generated worker Skills do not impose them, and they are not the contract for `kaola-project-runner`.
`templates/SKILL.md.tmpl` is the authoritative seven-platform communication-only contract.
`templates/orchestrator/` is the authoritative main-Skill contract.

Only platform facts may vary: executable, runtime carrier preflight, launch/continue/resume syntax,
TUI/editor/approval/session observation, graceful quit, and capability declarations. Unsupported
runtime-native recurring capability is reported as evidence; the invoking agent may still choose an
outer Codex carrier.

## Generated Skills

`render-skills.py` combines the active communication template, frozen optional references, fixed manifests, metadata templates, shared tmux
core, relay/client/protocol/observation helpers, and one matching adapter into seven self-contained
worker directories under `skills/`, and renders the fixed orchestrator directory
`skills/kaola-project-runner/` from `templates/orchestrator/` plus a supported-worker summary
derived from the seven manifests (no orchestrator platform manifest or adapter). Every managed
directory has a `.generated-by-kaola-project-runner` marker. A published Skill never follows a path
outside its own directory. The renderer refuses unmanaged targets and `--check` compares complete
byte inventories, including the orchestrator package.

`install-local.sh` delivers those directories to a consuming runtime: a verified named alias via
`--runtime` (`codex`, `claude-code`, `cursor`, `devin`), or any absolute `--skills-dir` (the two are
mutually exclusive; the flag-free default remains the Codex skills directory). `--method link`
(the default) symlinks each Skill to the checkout for development; `--method copy` installs the
identical payload as a standalone directory plus a per-Skill ownership/content receipt kept outside
the generated payload under `<skills-dir>/.kaola-install-receipts/`. Only an unmodified owned
installation is replaced or removed — user edits, foreign additions, and receipt-less paths are
preserved, and a `.generated` marker alone is never delete authority. Skill destination selection
(`--runtime`/`--skills-dir`) and target platform selection (`--platform`) are independent
dimensions: `--platform` filters worker Skills only. The main Skill is installed for every
destination unless `--no-orchestrator` is passed; its directory name is not a platform id.
Owned `$HOME/.local/bin/kaola-acp*` helper links are created only for the Codex runtime
destination or on explicit `--bin-links`; uninstall never removes them unless `--bin-links` is
passed, and then only exact-owned links.

## Session ownership

The core accepts `grok`, `claude-code`, `opencode`, `kimi-cli`, `cursor-cli`, `devin`, or `codex`. New sessions
receive:

```text
KAOLA_PROJECT_RUNNER=1
KAOLA_PROJECT_RUNNER_PLATFORM=<platform>
KAOLA_PROJECT_RUNNER_REPO=<canonical Git root>
KAOLA_PROJECT_RUNNER_MODEL_POLICY=<canonical JSON selection/provenance>
```

Observation reports exact session, owner, platform, repo, pane, cwd, relay, runtime child, and TUI
facts. These facts go to the agent rather than forming semantic authorization. Direct relay
transfers use the exact named single pane and current relay endpoint. The relay socket peer,
epoch and start fingerprint must match that pane; the nested child path, argv, PID/PGID and start
fingerprint must match the resolved runtime. Kimi's exact product-title exception remains limited to
its attested Node child. Scrollback, process basenames, and later argv text are never identity proof.

Snapshots and revisions correlate actions with evidence; they are not freshness gates. The Runner does
not classify runtime semantics: editor/activity/approval/decision/worker fields, coordinates, Git,
Workflow facts, and ordinary frame changes are advisory evidence and do not authorize or block generic
`send`/`stop`. A relay reports objective transfer outcomes. `answer --replace-editor` is
a separately measured transport capability, not a semantic decision engine. Grok retains its legacy
markers and JSON aliases.

## Measured relay transfer

The managed relay remains the pane leader and owns the CLI in a nested PTY, but ordinary communication
does not stop that child or create a prepare/submit transaction:

1. `observe` authenticates the relay and reads live relay/process/frame state without changing child,
   pane-input, or lease state;
2. the Runner proves exact session, repository, pane, relay, and child identity, then checks that the
   relay advertises direct-input capability;
3. `send`, `answer`, and graceful `stop` write one literal or bracketed-paste prompt followed by carriage
   return; `key` writes only the Agent-selected native key bytes;
4. the relay event loop serializes each request and returns the exact payload fingerprint. The Agent
   reads following output and decides its meaning.

Legacy quiesce/lease/fence operations remain an inactive protocol compatibility surface. They are not
called by normal Runner actions. A running legacy relay is readable and returns
`relay-upgrade-required` for mutation until the Agent chooses a safe exact-session restart.
The transport `pane_revision` and `snapshot_id` summarize visible and deterministic facts for
correlation. Output, input, editor, process, approval, decision, Git, and Workflow changes may advance
them, but no such change independently denies an agent-directed action. Later-output barriers remain
reported evidence rather than Runner-owned permission.

The relay attests the exact requested payload fingerprint. Payload validation rejects terminal
controls before PTY mutation; LF/TAB require attested bracketed paste. Placeholder and cursor
observations remain diagnostics for the agent rather than mutation gates. Force stop proves the exact
owned tmux identity, ends only that session, and reports any remaining relay/socket evidence without
classifying or sweeping processes.

## Failure model

Preflight, observation, and transfer report their exact facts and outcomes. A lost connection before a
direct-transfer receipt reports mutation as unknown rather than claiming non-execution. The Runner never installs
Kaola Workflow, guesses meaning from a process name, evaluates prompt text in a shell, rewrites user
configuration, or treats a supervision heartbeat as an execution loop. An absent session, unavailable
relay, legacy relay capability, disconnect, or unknown transfer outcome is reported as an objective
transport fact; a stale snapshot is not. Runtime-semantic uncertainty is given to the controlling agent
rather than converted into a Runner status gate. Cursor launch does not materialize or rewrite project
files; any installed authority or command surface is evidence for the Agent. Successful CLI prose,
Git cleanliness, or PR mergeability alone never proves a terminal Kaola run.
