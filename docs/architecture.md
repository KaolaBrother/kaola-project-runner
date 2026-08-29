# Architecture

## Product boundary

Kaola Project Runner is the Codex-facing orchestration layer around a runtime-native Kaola Workflow
installation. It does not implement Kaola Workflow and does not own a runtime's configuration.

```text
Codex Skill
    -> fixed platform adapter
        -> exact owned tmux main conversation
            -> runtime-visible workflow-next / kaola-workflow-finalize
                -> Git, Issue/PR, mission list, archive, and sink
```

Codex owns repository selection, exact-session control, observation, heartbeat lifecycle, and user
decision relay. The runtime main conversation owns project intake and execution. Kaola Workflow owns
claim, mission custody, validation, finalization, and repository lifecycle state.

## Grok golden contract

`templates/grok-golden/` is an immutable copy of the live-proven Grok Skill, metadata, lifecycle,
prompt, PR handoff, heartbeat, foreground scheduler, and closing references. The Grok generated
package must match these bytes exactly. New runtimes are mechanically aligned from the same complete
contract; shortening or semantically rewriting it is not an allowed form of platform adaptation.

Only platform facts may vary: executable, runtime carrier preflight, launch/continue/resume syntax,
TUI/activity/session detection, graceful quit, and capability declarations. Unsupported recurring
adapters retain the full parity target but carry an explicit fail-closed gate against emulation.

## Generated Skills

`render-skills.py` combines the golden contract, fixed manifests, metadata templates, shared tmux
core, and one matching adapter into five self-contained directories under `skills/`. Every managed
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
```

Reuse or mutation requires exact session, owner, platform, repo, one pane, pane cwd, and live TUI.
Live TUI identity requires both the adapter's observed title/current-command predicate and a current
pane process whose argv[0] or interpreter argv[1] binds the exact resolved runtime binary; scrollback
markers and later argv text are never identity proof. Kimi's fixed `kimi-code` process-title rewrite
is accepted only together with tmux's live `node` foreground command.
`send` additionally requires idle activity. Ordinary `stop` also requires idle and preserves an
unresolved `HUMAN_DECISION_REQUIRED`; `stop --force` bypasses graceful exit only and never bypasses
ownership checks. Claude decision classification combines pending-decision and editor evidence so a
prompt cannot override an unresolved decision; later runtime output must replace pending evidence in
the current activity tail before a fresh empty prompt clears stale history. Grok also receives the
legacy markers and legacy JSON aliases.

## Failure model

Preflight and ownership checks fail closed. The Runner never installs Kaola Workflow, adopts an
unowned session, guesses ownership by process name, evaluates prompt text in a shell, rewrites user
configuration, or treats a supervision heartbeat as an execution loop. Cursor's project catalog is
the narrow exception to ambient-write avoidance: an explicit new Cursor run uses the installed
Kaola authority's receipt-backed `--ensure-target` transaction before tmux creation, and refuses
unmanaged collisions. The materializer helper itself must be present in the authority receipt with
its exact path, SHA-256, and mode before the Runner may execute its doctor or materialization entry
point. Successful CLI prose, Git cleanliness, or PR mergeability alone never proves a terminal
Kaola run.
