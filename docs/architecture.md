# Architecture

## Product boundary

Kaola Project Runner is the Codex-facing orchestration layer around a runtime-native Kaola Workflow
installation. It does not implement Kaola Workflow and does not own a runtime's configuration.

```text
Codex Skill
    -> fixed platform adapter
        -> exact owned tmux pane leader: managed relay
            -> attested nested-PTY runtime child
                -> runtime-visible workflow-next / kaola-workflow-finalize
                    -> Git, Issue/PR, mission list, archive, and sink
```

Codex owns repository selection, semantic interpretation of raw observations, exact-session control,
heartbeat lifecycle, and user decision relay. The Runner owns deterministic evidence, snapshot
comparison, and transport safety. The runtime main conversation owns project intake and execution.
Kaola Workflow owns claim, mission custody, validation, finalization, and repository lifecycle state.

## Grok golden contract

`templates/grok-golden/` is an immutable copy of the live-proven Grok Skill, metadata, lifecycle,
prompt, PR handoff, heartbeat, foreground scheduler, and closing references. Prompt, task-mode,
scheduling, handoff, and lifecycle bytes remain frozen. A narrow, anchor-checked and independently
reversible transport overlay updates only generated instructions that previously treated idle as
input authority. New runtimes are mechanically aligned from the same complete contract; shortening
or semantically rewriting it is not an allowed form of platform adaptation.

Only platform facts may vary: executable, runtime carrier preflight, launch/continue/resume syntax,
TUI/editor/approval/session detection, graceful quit, and capability declarations. Unsupported recurring
adapters retain the full parity target but carry an explicit fail-closed gate against emulation.

## Generated Skills

`render-skills.py` combines the golden contract, fixed manifests, metadata templates, shared tmux
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
```

Reuse or mutation requires exact session, owner, platform, repo, one pane, pane cwd, managed relay,
runtime child, and live TUI. The pane process must bind the exact relay path; the relay socket peer,
epoch and start fingerprint must match that pane; the nested child path, argv, PID/PGID and start
fingerprint must match the resolved runtime. Kimi's exact product-title exception remains limited to
its attested Node child. Scrollback, process basenames, and later argv text are never identity proof.

Every mutation requires a caller-inspected schema-v2 snapshot. `send` requires an empty editor;
ordinary `stop` refuses nonempty/unknown editor and active/unknown work; force stop bypasses graceful
work guards but not snapshot or identity. `answer` is a separate, capability-gated replace operation.
`activity_hint` never authorizes mutation. Grok retains its legacy markers and JSON aliases.

## Atomic compare-and-act

tmux immediately resumes a stopped pane leader, so directly signaling the CLI cannot establish an
atomic boundary. The managed relay remains running as pane leader and owns the CLI in a nested PTY:

1. disable tmux pane input and stop the exact runtime child tree, recursively fingerprint-tracking
   descendants even when they escape the original process group;
2. drain and forward all nested-PTY output;
3. send a random tokenized DECRQM query and wait for tmux's exact nonce reply, proving its parser
   consumed every preceding relay byte without changing grid/cursor/history;
4. rebuild and compare the complete snapshot while the child remains stopped;
5. apply action guards, prepare literal/bracketed input, rebuild and revalidate the prepared surface,
   verify that the visible editor is the exact prepared payload for send or answer, submit Enter,
   then resume the child and restore pane input.

The relay lease restores the child and input after refusal, disconnect, timeout, or caught failure.
The transport `pane_revision` covers the complete visible pane plus output offset/digest, history,
resize, and relay epoch. The mutation `snapshot_id` separately binds visible frame/editor/cursor,
exact ownership and child identity, input offset, resize, process tree, approval/decision/barrier,
and Git facts. Output-only equivalent redraws therefore advance `pane_revision` without denying a
safe action; silent input or any mutation-relevant change still stales the token. Later-output
barriers use output advance plus visible-frame revision, not activity prose.

The fence consumes exactly one nonce reply and also checks a separately queued next outer read.
Any other outer-pane input appearing inside the fence-to-submit window aborts or is discarded without
replay. Prepared editors bind the exact requested payload fingerprint; tmux soft-wrap rows are
joined without joining real payload newlines. Payload validation rejects terminal controls before PTY mutation;
LF/TAB require attested bracketed paste. Placeholder recognition also binds cursor position, so
painted suggestions cannot make identical typed text look empty. Force-stop terminal proof includes
all exact tracked descendants, not only the original child PGID.

## Failure model

Preflight, relay attestation, observation, and restoration checks fail closed. The Runner never
installs Kaola Workflow, adopts an unowned or legacy-direct session, guesses ownership by process
name, evaluates prompt text in a shell, rewrites user configuration, or treats a supervision
heartbeat as an execution loop. A stale snapshot, unavailable terminal fence, uncertain editor,
relay disconnect, or unknown submit outcome is a refusal rather than an idle inference. Cursor's project catalog is
the narrow exception to ambient-write avoidance: an explicit new Cursor run uses the installed
Kaola authority's receipt-backed `--ensure-target` transaction before tmux creation, and refuses
unmanaged collisions. The materializer helper itself must be present in the authority receipt with
its exact path, SHA-256, and mode before the Runner may execute its doctor or materialization entry
point. Successful CLI prose, Git cleanliness, or PR mergeability alone never proves a terminal
Kaola run.
