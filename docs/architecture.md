# Architecture

## Product boundary

Kaola Project Runner is a Codex-facing CLI communication driver. It does not orchestrate Kaola
Workflow, implement Workflow, or own a runtime's configuration.

```text
Controlling Agent
    -> communication-only Codex Skill
        -> fixed platform adapter
        -> exact owned tmux pane leader: managed relay
            -> attested nested-PTY runtime child
                -> Agent-selected prompt, key, or optional Workflow command
```

The controlling Agent owns every command, orchestration, heartbeat, recovery, decision, and completion
choice. The Runner owns exact-session control, evidence collection, prompt/key transfer, response
readback, and truthful mechanical receipts. Kaola Workflow owns lifecycle state only when the Agent
chooses to invoke it.

Main-model choice is a per-run transport fact. A current-request user override wins; otherwise the
adapter's declared Runner default is resolved from the current catalog. The selection enters the
child as literal argv plus narrowly scoped invocation parameters, never by rewriting global CLI
configuration. Runtime-owned post-launch evidence is returned to the Agent and does not become
permission to use the communication channel.

## Grok golden contract

`templates/grok-golden/` is an immutable historical copy of the live-proven Grok Skill, metadata, lifecycle,
prompt, PR handoff, heartbeat, foreground scheduler, and closing references. Project prompt, task-mode,
scheduling, handoff, and lifecycle bytes. Those bytes remain frozen as reference evidence; active
generated Skills do not impose them. `templates/SKILL.md.tmpl` is the authoritative five-platform
communication-only contract.

Only platform facts may vary: executable, runtime carrier preflight, launch/continue/resume syntax,
TUI/editor/approval/session observation, graceful quit, and capability declarations. Unsupported
runtime-native recurring capability is reported as evidence; the invoking agent may still choose an
outer Codex carrier.

## Generated Skills

`render-skills.py` combines the active communication template, frozen optional references, fixed manifests, metadata templates, shared tmux
core, relay/client/protocol/observation helpers, and one matching adapter into five self-contained
directories under `skills/`. Every managed
directory has a `.generated-by-kaola-project-runner` marker. A published Skill never follows a path
outside its own directory. The renderer refuses unmanaged targets and `--check` compares complete
byte inventories.

## Session ownership

The core accepts only `grok`, `claude-code`, `opencode`, `kimi-cli`, or `cursor-cli`. New sessions
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
