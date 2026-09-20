# Architecture

## Product boundary

Kaola Project Runner is a runtime-neutral Agent Skills CLI communication driver: any agent that
can load a skill directory and run shell commands in an environment containing the target CLI can
use the same ten worker Skills, and Codex remains a fully supported consuming runtime. A separate
generated control-plane Skill, `kaola-project-runner` (display name Project Runner), supervises
explicitly authorized workers through those transport Skills. Worker Skills do not orchestrate
Kaola Workflow, implement Workflow, or own a runtime's configuration.

```text
Host Agent
    -> optional main Skill kaola-project-runner (heartbeat, dispatch, acceptance, close-out)
        -> communication-only worker Agent Skill
            -> manifest-selected transport
                -> ACP holder + structured protocol agent
                   (Claude Code: the vendored claude-code-acp bridge shipped in the Skill,
                    one exact `claude -p` subprocess per turn under the user's subscription;
                    ZCode: Skill-relative kaola-zcode-acp.py over explicit app-server --stdio)
                OR
                -> fixed platform adapter
                    -> exact owned tmux pane leader: managed relay
                        -> attested nested-PTY runtime child
            -> Agent-selected prompt, key, or optional Workflow command
```

The controlling Agent owns every command, orchestration, heartbeat, recovery, decision, and completion
choice. When the main Skill is in use, that Skill states how the host Agent recovers authorization,
dispatches workers, accepts work before finalize, prefers selected Workflow sync/merge when a PR
is not required, advances actionable open PRs on contested capacity in parallel with other
authorized work, stops leftover idle owned sessions (including ACP), and defaults to finishing
in-hand issues with a clean workspace close-out after a run.
The Runner owns exact-session control, evidence collection, prompt/key transfer, response
readback, and truthful mechanical receipts. Kaola Workflow owns lifecycle state only when the Agent
chooses to invoke it.

ACP Watch（见 `docs/acp-watch/` / issues #25–#27）：人类旁观订阅 holder 上的投影，不得成为第二条 agent stdio 客户端，也不得把原始 `session/update` 塞进 Skill 热路径。permit lock（#25）、`list`/`view`（#26）与本机 `follow`（#27）已实现。PTY 仍是登录与原生 TUI 接管。

Main-model choice is a per-run transport fact. A current-request `--model` wins; otherwise
`--tier default|upgrade` selects the manifest's declared preset (`default` when unset), resolved
against the current catalog; a platform may declare one further preset under its own word
(`alt_tier_label`, e.g. `--tier alternative`, `--tier fable`), and a tier the platform does not
declare is refused by name rather than resolved to `default`. `--effort` applies only to the model selected in the same request, and
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
`templates/SKILL.md.tmpl` is the authoritative ten-platform communication-only contract.
`templates/orchestrator/` is the authoritative main-Skill contract.

Only platform facts may vary: executable, runtime carrier preflight, launch/continue/resume syntax,
TUI/editor/approval/session observation, graceful quit, and capability declarations. Unsupported
runtime-native recurring capability is reported as evidence; the invoking agent may still choose an
outer Codex carrier.

ACP mode and permission option IDs are manifest-driven: every worker manifest declares
`acp_mode_config_id` (for example, Droid uses `autonomy_level`; platforms without an ACP mode
option leave it empty). The ACP holder no longer assumes one global mode/config ID, while the
existing eight platforms retain byte-identical behavior.

## Generated Skills

`render-skills.py` combines the active communication template, frozen optional references, fixed manifests, metadata templates, shared tmux
core, relay/client/protocol/observation helpers, and one matching adapter into ten self-contained
worker directories under `skills/`, and renders the fixed orchestrator directory
`skills/kaola-project-runner/` from `templates/orchestrator/` plus a supported-worker summary
derived from the ten manifests (no orchestrator platform manifest or adapter). It also emits
the Grok Bot host bundle `hosts/grok-bot/`: one thin bridge Skill
`kaola-delegator.md`, its fingerprint manifest `bridge.json`, and the install guide
`INSTALL.md`. It also renders `skills/kaola-delegator/` from
`templates/kaola-delegator/`. Every managed
directory has a `.generated-by-kaola-project-runner` marker. A published Skill never follows a path
outside its own directory. The renderer refuses unmanaged targets and `--check` compares complete
byte inventories, including the orchestrator package and `hosts/grok-bot/`.

The ten-worker inventory includes Claude Code, Codex, Cursor CLI, Devin, Droid, dsh, Grok CLI,
Kimi CLI, OpenCode, and ZCode. Droid uses the native ACP agent `droid exec --output-format acp`
as its default transport and keeps PTY as an explicit fallback. dsh uses its shipped automation-only
ACP profile `dsh --profile acp` and has no PTY transport at all: no terminal UI exists for it, so
`--transport pty` is a diagnostic entry only.

Grok Bot is a **bridge host** for Kaola-Delegator, not a Project Runner host.
Research on Grok Bot 0.51.0 found `NO_SUPPORTED_PATH` for
automated account-Skill creation, so the account receives exactly **one** very small Skill
(`hosts/grok-bot/kaola-delegator.md`): it names the repository, the expected origin, the
accepted pinned revision, the device-local locator command `kaola-project-runner-locate`, and
the one canonical entry path `ROOT/skills/kaola-delegator`. It binds the execution target first (Local
Computer or the cloud Agent Computer; neither reaches the other's files, CLIs, tmux, or
sessions, and the cloud never installs or updates the Mac), asks that target's locator for the
verified ROOT, accepts the consumer project root separately on the same target, and loads
only the Kaola-Delegator Skill from that checkout. That Skill starts one ZCode Host which
loads Project Runner internally. `scripts/
kaola-locate.py` is the locator and the fail-closed host-target attestation (bounded receipt:
target kind as declared, host fingerprint to compare with the registered one, ROOT identity,
project identity, worker script under the same ROOT, session presence; real local paths, no
credentials; it does not classify physical host kind). `register --target local|cloud`
validates before it links and then writes a credential-free registration receipt beside the
link (resolved ROOT, declared target, host fingerprint, accepted revision) that every later
call compares with the running host and declared target, failing closed on mismatch.
The bridge follows a two-commit content/pin model (`accepted-revision.json` stage `content`
for the content commit R, stage `pinned` for the pin commit P that names R; the pin gate in the
renderer and verifier proves R exists, is an ancestor, is a content-stage commit, holds the
locator and every entry path, and differs from P only by `accepted-revision.json` plus the
three generated products with a one-line bridge diff; an accepted R/P pair is never rebased or
squashed, and a moved `main` means a fresh R/P). Grok Bot is a **host**, not a tenth platform: there is
no `platforms/grok-bot.yaml`, no transport adapter, no runtime copy, no per-worker account
Skills, and no installer destination. `scripts/kaola-grok-bot-verify.py` proves the bridge
shape and budgets and, with `--repo`, byte identity with a fresh render. `--platform grok`
still selects the Grok CLI worker. A saved bridge is not live adoption; the owner's read-only
Local Computer UAT is the boundary. See [Grok Bot host](grok-bot-host.md).

ZCode is additionally a native skill-directory **Host** (Issue #62): `--runtime zcode` installs
to `~/.zcode/skills`, and the live-verified default workspace `.zcode/skills` and `.agents/skills`
discovery roots go through `--skills-dir`; see [ZCode host](zcode-host.md). Nested Host→Worker isolation is a
process/session **contract** verified by an offline harness: an inner Runner session started
under an outer holder is a separate session with its own record-root entry and process
group. When the outer holder's agent starts the inner session, the nested start appends the
inner holder's identity (`pid`, `pgid`, `spawned_at`) to the outer holder's `children.jsonl`
(via `KAOLA_ACP_CHILD_RECORD`), so an inner stop never reaches the outer Host and the outer
stop sweeps only recorded inner holders — the holder-lost `stop --force` path uses the same
identity-checked record. `KAOLA_ACP_CHILD_RECORD` is a write handle to a holder record: only a
holder sets it for its own agent, and the ZCode adapter never forwards it to the app-server
child. The second holder→agent fact, `KAOLA_ACP_DISPATCHER` (Issue #104), is identity only —
`holder_instance_id`, `platform`, `repo`, `session` — and the ZCode adapter does forward it: the
socket it implies is already deterministic from those strings, so it grants nothing, and it is
what lets a worker `start` run inside the Host bind back to the Host mechanically (refusing,
rather than opening unbound, when that holder is not live). Real model-driven Host dispatch (a Host Agent actually delegating a turn to a Worker)
is deferred to controlled live E2E, not emulated by executing prompts. The three session
layers stay separately trackable: the Runner session name, the ACP session id, and the native
`sess_*` id (reported credential-free as `native_session_identity`).

### Progressive disclosure

Discovery exposes only a stable name and a short description. Activating Project Runner
loads its body only, never a worker body. Selecting one worker loads that worker only.
References load only when the current operation needs them. Scripts execute mechanically;
the model never reads their source. Observe, status, capture, and verifier outputs are
bounded receipts (hashes, counts, relevant excerpts), never whole files or unbounded terminal
history, on both transports: PTY `capture` through `kaola-observation.py bound-text` and PTY
`observe`/`status` through `bound_observation` (newest frame lines and first process entries
kept, `truncated.fields` with sizes and sha256, `snapshot_id` from the full frame); ACP
`capture` through `bound_capture_receipt` and ACP `observe`/`status` through
`bound_state_receipt` in `kaola-acp.py` (oldest entries dropped or structures summarised by
size and sha256 under a `truncated` block); `capture --full` is the only explicit exception. Host adapters may not flatten,
concatenate, eagerly preload, or duplicate canonical Skill bodies for packaging convenience.
`templates/budgets.json` declares the measurable byte budgets (descriptions, main Skill, each
worker, each reference, bridge, guide, locator receipt, ordinary capture receipt);
`render-skills.py --check` and `tests/contract/test-progressive-disclosure.py` fail when a
budget or a loading boundary regresses.

### Host adapters: one canonical Skill system

There is exactly one canonical Skill system: `templates/orchestrator/` (the main Skill and its
references), `templates/SKILL.md.tmpl` with `templates/agents/` and `templates/references/` (the
worker contract), the ten `platforms/*.yaml` manifests, and the shared `scripts/`. A **host
adapter** re-packages that system for one host inside `render-skills.py`; it never authors a
second body. Grok Bot is such a packaging adapter (the delimited "Host adapter: grok-bot" section
of the renderer), not a CLI transport platform: there is no `platforms/grok-bot.yaml` and no
`scripts/adapters/grok-bot.sh`. The adapter's inputs are exactly `GROK_BOT_ADAPTER_INPUTS` = `templates/grok-bot/` (bridge
template, install-guide template, accepted revision): its product functions take no platform
manifest, read no canonical source, and copy nothing (the guide uses a `<platform id>`
placeholder). Its outputs are the bridge, `bridge.json`, and `INSTALL.md`. Host differences live
only in that adapter layer (target binding, locator, one-write install steps); scheduling,
safety, and transport semantics stay in the canonical sources and are loaded on demand from
the verified checkout. `--write` owns every product, `--check` rejects any product that drifts
from a fresh render or exceeds its budget, and `scripts/kaola-grok-bot-verify.py --repo` proves
the same from outside the renderer. Tests (`Issue49BridgeInvariance`, `Issue49PinModel`) prove
that a canonical or manifest edit leaves all three products byte-identical, that a new pin
changes exactly one line, and that the pin gate refuses a missing, non-ancestor, incomplete,
self-pinned, or wrongly tagged commit. The canonical half of that probe uses equal-length
substitutions so it cannot spend `main_skill_bytes` (Issue #71); `templates/budgets.json`
remains the only ceiling.

`install-local.sh` delivers those directories to a consuming runtime: a verified named alias via
`--runtime` (`codex`, `claude-code`, `cursor`, `devin`), or any absolute `--skills-dir` (the two are
mutually exclusive; the flag-free default remains the Codex skills directory). `--method copy`
(the default) installs the identical payload as a standalone directory plus a per-Skill
ownership/content receipt kept outside the generated payload under
`<skills-dir>/.kaola-install-receipts/`; `--method link` is the explicit development choice that
symlinks each Skill to the checkout. An owned source link migrates to a copy on a default or
`--method copy` reinstall. Only an unmodified owned installation is replaced or removed — user
edits, foreign additions, and receipt-less paths are preserved, and a `.generated` marker alone is
never delete authority. Skill destination selection
(`--runtime`/`--skills-dir`) and target platform selection (`--platform`) are independent
dimensions: `--platform` filters worker Skills only. The main Skill is installed for every
destination unless `--no-orchestrator` is passed; its directory name is not a platform id.
Owned `$HOME/.local/bin/kaola-acp*` helper links and the `kaola-project-runner-locate`
locator link are created only for the Codex runtime destination or on explicit `--bin-links`; uninstall never removes them unless `--bin-links` is
passed, and then only exact-owned links.

## Session ownership

The core accepts `grok`, `claude-code`, `opencode`, `kimi-cli`, `cursor-cli`, `devin`, `codex`, `zcode`, `droid`, or `dsh`. New sessions
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

## Canonical project root and Workflow child worktrees

`--repo` must name a Git top-level. The ordinary Workflow default is the consuming project's
**canonical project root** (the main checkout). A Workflow **child worktree** is also a Git
top-level; starting there is an Agent decision, not a transport refusal, on both PTY and ACP.
`KAOLA_PROJECT_RUNNER_REPO` is the realpath of the Agent-selected `--repo`, not a classifier that
the path is the canonical project root.

A Project Runner Orchestrator states the root explicitly instead, by exporting
`KAOLA_PROJECT_RUNNER_CANONICAL_REPO=<abs root>` once at setup. `scripts/kaola-tmux.sh` — the one
entrypoint both transports and all ten platforms pass through — then resolves that binding and the
requested `--repo` with `realpath`, requires the binding to be a Git top-level, completes an omitted
`--repo` from it, and on `start` compares the two exactly. A different root, including a linked
worktree of the same repository, returns a typed `canonical-root-mismatch` refusal (an unusable
binding returns `canonical-root-invalid`) with `mutation_performed: false` before any process,
tmux session, or record exists; an accepted dispatch reports `canonical_repo` in its receipt.
Without that export nothing changes: standalone starts, existing sessions, and close-out of a
legacy worktree-rooted session by its own `--repo` behave exactly as before. The binding guards
against accidental dispatch drift; it is not protection against a hostile controlling host, and it
adds no registry, lock, or daemon.

Inspect `git worktree list`, Workflow `workflow-state.md` / `mission-list.md`, and existing exact
sessions before choosing where to start. Then, for ordinary Workflow-backed work, start at the
canonical project root and ask that runtime's main conversation to invoke `workflow-next` so its
Workflow creates or recovers the child worktree. Several exact sessions may share one canonical
project root with distinct Workflow-owned worktrees. Path shape such as `.kw/worktrees` is not a
security boundary. See the generated orchestrator reference
`skills/kaola-project-runner/references/workflow-worktree.md`.

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
