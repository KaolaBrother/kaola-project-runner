# Conventions

## Change boundary

The existing Grok Workflow contract is golden and live-proven historical evidence. Do not rewrite its
bytes. It is not the active Runner authority: all ten worker Skills use the shared communication-only
template and do not impose task modes, prompts, PR handoff, heartbeat, scheduler, or closing policy.
Project-level heartbeat, acceptance, Workflow merge preference with conditional open-PR priority, idle-session stop, and end-of-run close-out live in the generated main Skill `kaola-project-runner`.

## Source of truth

- Active ten-platform worker Skill: `templates/SKILL.md.tmpl`.
- Main orchestrator Skill: `templates/orchestrator/` (English `SKILL.md.tmpl`; not a platform
  manifest or adapter).
- One canonical Skill system, host adapters for packaging: every host output is derived by
  `render-skills.py` from the orchestrator template, the worker template, the platform manifests,
  and their canonical references. A host adapter (the delimited "Host adapter" section of the
  renderer) may add only host-specific packaging — reference expansion, path hints, account form,
  fingerprints, install steps — never a second hand-written body and never scheduling, safety, or
  transport semantics. Products are owned by `--write`, rejected on drift by `--check` and the
  host verifier, and updated automatically when a canonical source changes.
- External Kaola-Delegator Skill: `templates/kaola-delegator/` renders
  `skills/kaola-delegator/` (display name Kaola-Delegator). It is a thin handoff to one
  CLI Host of any supported platform (#187) and is not a second control-plane engine.
- Grok Bot host bundle: `hosts/grok-bot/` rendered by the `grok-bot` host adapter (inputs:
  `GROK_BOT_ADAPTER_INPUTS` = `templates/grok-bot/` only) — one thin bridge Skill
  `kaola-delegator.md`, `bridge.json`, and `INSTALL.md`. The bridge carries the accepted
  revision from `templates/grok-bot/accepted-revision.json` under a two-commit content/pin model
  (stage `content` for the content commit R, whose bridge is not saveable; stage `pinned` for
  the pin commit P that names R with an honest label or release tag; `--check --require-pinned`
  is the gate for P) and no canonical content. Grok Bot is a bridge host, not a `platforms/*.yaml` worker and not an installer
  destination; there is no `platforms/grok-bot.yaml`, no `scripts/adapters/grok-bot.sh`, and
  no `--runtime grok-bot`. `scripts/kaola-locate.py` is the device-local locator and
  host-target attestation.
- Progressive-disclosure budgets: `templates/budgets.json`, enforced by `render-skills.py
  --check`, the host verifier, and `tests/contract/test-progressive-disclosure.py`.
  Host-invariance probes in `tests/contract/test-issue-49-grok-bot-host.py` mutate
  canonical sources with equal-length substitutions and do not reduce those numbers.
- Frozen historical Workflow lifecycle and prompts: `templates/grok-golden/`.
- Shared ACP transport guidance: `templates/references/acp.md.tmpl` and `templates/SKILL.md.tmpl`
  (the PTY `transport.md.tmpl` reference was removed in Issue #130); never broad-replace golden prose.
- Fixed runtime facts: one `platforms/*.yaml` manifest.
- Every manifest includes the `acp_mode_config_id` key so ACP mode/permission option IDs remain
  platform-specific; empty values record platforms whose agents expose no ACP mode option.
- Executable differences: one `scripts/adapters/*.sh` adapter.
- `skills/`: generated, committed output; never hand-edit it.
- Workflow commands and roles: the Kaola Workflow distribution, not this repository.

After an allowed source change:

```bash
./scripts/render-skills.py --write
./scripts/validate.sh
```

## Progressive disclosure

**Progressive disclosure.** Discovery exposes only a stable name and a short description.
Activating Project Runner loads its body only, never a worker body. Selecting one worker loads
that worker only. References load only when the current operation needs them. Scripts execute
mechanically; the model never reads their source. Observe, status, capture, and verifier
outputs are bounded receipts: hashes, counts, and relevant excerpts, never whole files or
unbounded history; an over-budget receipt keeps its newest part
and names the rest in a `truncated` block with counts and sha256 (`capture --full` is the
explicit, requested exception). Host adapters may not flatten,
concatenate, eagerly preload, or duplicate canonical Skill bodies for packaging convenience.
Every platform adapter and host declares measurable byte budgets for discovery, activation,
selected-worker increment, references, and tool outputs in `templates/budgets.json`;
`render-skills.py --check` and the contract tests fail when a budget or a loading boundary
regresses. A bridge host (Grok Bot) binds its execution target first and loads
`skills/kaola-delegator` from a verified checkout on that target; nothing is
copied into the account. Grok Bot does not load Project Runner or a worker Skill
from the bridge.

## Shell safety

Use macOS-compatible Bash with `set -euo pipefail`. Platform IDs use fixed dispatch. Canonicalize
repositories and prove the Git top-level. Send prompt text as ACP stdio JSON-RPC through the exact
session's holder, never interpolation or `eval`. Do not use basename-only ownership or process-name
adoption; stop acts only on the exact recorded holder, agent group, and identity-checked child groups.
The PTY transport is retired (Issue #130): a `--transport pty` request is refused
`transport-pty-retired` before anything exists. Captured output, approval/activity labels, worker
counts, and later argv text are evidence for the controlling agent, not Runner semantic authority.
Generic send/stop may not branch on those advisory fields.

`scripts/kaola-tmux.sh` carries no here-document and no here-string. Bash writes a heredoc body up
to 4096 bytes into a pipe from the forked child before `exec`, so that one process holds both ends
and nothing drains it; macOS hands out 512-byte pipes under pipe-KVA pressure, and a larger body
then blocks in `write()` forever, leaving a child that wears the script's argv and outlives a
SIGKILL aimed at its parent (Issue #78). Pass Python programs with `-c` and feed `read` from a
process substitution.

Each platform Skill must teach the same measured loop: start, observe/capture, let the Agent decide,
send the chosen prompt, observe/capture the response, and stop the exact session when the
Agent chooses. Workflow/Git/forge verification occurs only when the Agent chose a Workflow task.
Activity and retained drafts are evidence, never Skill-owned policy gates. The same Skills
recommend — never require — stopping owned runtime once delegated work is delivered, keeping
already-available resume facts (native session ID is not the Runner session name); `stop` never
deletes history, and resume stays the Agent's choice among `--resume`, `--continue`, or a fresh
session.

Model mismatch, unreadable actual-model evidence, login failures, and resume behavior are likewise
facts for the controlling Agent. Never turn them into a start/send/observe/stop gate or rewrite the
Agent-selected model literal.

## Canonical project root and Workflow child worktrees

Ordinary Workflow-backed work starts the worker at the consuming project's canonical project root
and asks that runtime to invoke `workflow-next` in-session. The worker's Workflow owns the child
worktree. Linked-worktree starts and existing-run recovery are Agent decisions, not transport
gates. Do not add a `.kw/worktrees` refusal to adapters or
runtime scripts. Change this guidance through `templates/orchestrator/` and `templates/SKILL.md.tmpl`,
then `./scripts/render-skills.py --write`.

## Issue-scoped dispatch names

Every new issue-backed ACP dispatch decides its real open issue first and names the session
`<platform>-<PROJECT>-i<ISSUE>-<unique-purpose>`, where `PROJECT` is the stable short code the
consuming project's heartbeat declares beside its canonical repository identity; the name is
verified in the start receipt and reused on later dispatches and same-issue restarts. One
Workflow run claims one real issue, and several workers may share that issue's run and Mission
List under distinct names and native sessions. This is scheduling policy carried by the main
Skill and the rendered heartbeat (`templates/orchestrator/references/issue-dispatch.md`): the
ten worker Skills gain no classifier, the 1-80 `--session` syntax is the only validator, no
registry, daemon, or Workflow state field is added, and a running session is never renamed or
restarted to adopt the rule. Whether any consumer displays issue-run progress from these names
is outside this repository and is not verified here.

## Release notes

### State-format updates and migration

Any version that changes project state formats or the rules interpreting them must ship an
explicit, verified upgrade path for existing projects. This includes the Delegator and Host
JSON files, authorization and role semantics, and their heartbeat entry templates. Document
the supported source versions or schemas, the target format, when migration runs, and any
required holder update or safe restart. Do not claim an upgrade complete merely because new
Skill files were installed.

- Include old-format detection and migration instructions in the normal installation/update
  and first-load recovery flow. Coordinate state adoption with the actual loaded Skill and
  holder capabilities; do not expose an incompatible format to an old reader.
- Preserve effective user authorization, goals, active and pending responsibilities,
  in-flight session/dispatch associations, unresolved holds and warnings, and user schedule
  settings. Reconcile with existing Runner, Git, forge and Workflow evidence; do not reset a
  project, repeat admitted work, or automatically replan it because its storage format changed.
- Replace superseded instructions and duplicate history only with supporting evidence.
  Preserve unresolved ambiguities for review. Migrate already-evidenced user requirements
  without asking the user to confirm the same decision again.
- Prepare and validate the new state before replacing the old state. Keep the necessary
  migration source evidence once, make interrupted/repeated migration recoverable without
  duplicate effects, and provide an actionable recovery path if migration cannot finish.
  Do not restart or stop healthy in-flight work merely to reorganize state.
- Verify at least a representative supported old state, in-flight work, unresolved exceptions,
  interrupted/repeated migration, and incompatible-reader handling. Report the actual source
  and target versions, preserved associations, unresolved items and outcome using existing
  upgrade evidence; add no permanent second state ledger.

This is a release/update requirement. For the lifecycle state of
[#255](https://github.com/KaolaBrother/kaola-project-runner/issues/255) (`docs/designs/lifecycle-state-2026-10-04/`):

- Source `kaola-heartbeat-prompt/1` (a `body` string holding `project`, `authorization`,
  `active`, `pending`, `recovery`); target `kaola-heartbeat-prompt/2` (structured `state` plus a
  generated Host-view `body`, so old readers still receive a string `body`).
- Migration runs at the first load of the updated Skill, at a safe handoff point, through
  `kaola-dispatch.py state migrate --file <project>/.kaola/heartbeat-prompt.json --index <index>
  --live <list>`. Without `--write` it is a read-only plan; with `--write` it maps each `active`
  row to one `doing` task that keeps its assignment locator and known fields, keeps each
  `pending` row with its stated stage (else `todo`, with the unknown stage listed), keeps
  `recovery.protected_untracked` when it is a list of non-empty strings, and lists unknown keys,
  unassociated index rows and any v1 Sideagent binding not proven by `authorization_source`
  plus its exact live holder as `unverified` locators. Other legacy field names leave and are
  not copied. An unresolved critical mapping writes nothing and leaves the original file
  intact. Do not write `heartbeat-prompt.v1-<sha12>.json` or `recovery.migration.raw`.
  `state-overwritten` is not raised from those copies; overwrite detection is reduced and
  recovery uses project, Runner, and forge records. Existing hash-named copies are not
  deleted or trusted (`state backups`). A clean repeat reports `current`; an unreadable file
  is left unchanged and reported, and any schema other than v1 or v2 is refused
  (`schema-unsupported`) rather than read as v1.
- Holder: the v2 file may exceed 64 KiB after migration records a live Host holder that
  advertises `heartbeat-state/2` as `carrier`. `state migrate` without `--live` uses the
  1 MiB bound and does not treat the missing list as an old holder. An older holder named by
  `--live` keeps the 64 KiB whole-file limit (`carrier-limit`). Adoption path: restart the
  Host holder on the new build at a safe point, then run `state migrate --write --live <list>`
  to record the carrier.
  Healthy workers are not restarted for migration; they get the new holder behavior at
  their next normal start.
- Host replacement: the new Host runs `rebind-host` on each existing seat from its own session;
  the carrier moves in place and the worker is not restarted. Only the carrier moves: the
  seat's `dispatcher` still names the old Host, each seat (the Sideagent included) needs its own
  call, and worker events staged in a Host holder that died stay there; the new Host adopts
  that work from the index and receipts. A holder older than that op answers `unknown-op` and
  keeps the previous recovery (`drain-restart` at idle).
- A v1 `pending` key with no v1 meaning is not copied onto the task and does not take effect,
  including a key that shares a v2 field name (`verdict`, `dispatch`, `keep_open`). Its name
  is an `unverified` locator. It is not stored under `legacy`.
- Consolidated #255 fields are additive and need no `--write` migration: a file without
  `host_revision`, `maintenance`, `dispositions` or `writer_holder` reads as revision 0 with
  no checkpoint, and the first Host business write starts the count. A Sideagent binding
  without `"mode": "node"` keeps the relay path; node mode needs a Host holder advertising
  `sideagent-node/1`, and `--preserve-dispatched-workers` needs `preserve-dispatched/1`
  (an older live holder refuses it with `preserve-unsupported` and stops nothing). Adopt both
  by `drain-restart` of the Host holder at idle; an older reader of the index ignores
  `prompt_source`, `acceptance_source` and the new `collect` result keys.
- A continuing Sideagent started on a pre-#255 holder sweeps the child process groups it
  tracked when it stops, so `stop` or `drain-restart` of it also ends any worker it started.
  Retire it only once no such worker runs: list `kaola-acp.py list --repo` rows whose record
  `dispatcher` names its holder (or whose holder descends from its agent), let each finish,
  `collect` it and exact-stop it after the Host's disposition, then stop the Sideagent and bind
  node mode or a successor under a new name. While such a worker must keep running, mark the
  binding `replacing` (the Host view lists it) and leave the old Sideagent running, unsent,
  until that worker ends. Never adopt its work by restarting it.
- Shown live in isolated fixtures (#255): fresh nodes on Codex and ZCode; preserve stop,
  `rebind-host` and worker survival with Codex and ZCode Hosts; a model-driven Codex Host
  with a Codex node binding running two workers and judging their originals. Not yet verified on a real
  project: the other platforms, relay across holder death, candidate native timer read-back,
  real state size and migration of a real project.

### Release labels and running seats

Every `CHANGELOG.md` release section states whether running seats must restart,
as its own line: `Seats: restart required` or `Seats: restart not required`.
Seats must restart when the holder, the ZCode bridge, or the ACP protocol
changed, or when `kaola-quota.py` changed - the holder pins that catalog at
startup (Issue #162), so a running seat only picks up its new bytes by
restarting. The holder also pins `scripts/kaola-record-contract.py` at startup
(Issue #259). A running seat picks up a new projection only by restarting.
That file is outside the operator diff. The operator test is a non-empty diff:

```bash
git diff OLD NEW -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms
```

`OLD` and `NEW` are the previous release tag and the commit being released.
A pin bump whose holder, bridge, and protocol are byte-identical still says
`Seats: restart not required` when that diff is empty: running seats keep the
code they started with, and the note is what tells the operator they may stay
up. The note is part of cutting the release. It does not itself tag or publish.

## Tests and live evidence

Behavioral changes require baseline-failing acceptance. Offline tests use temporary repositories,
fake ACP agents, isolated homes and ACP record roots (`KAOLA_ACP_RECORD_ROOT`), and public
transport commands; a test that starts a real holder registers its force-stop cleanup first.
Real runtime tests record version, holder/agent identity, ACP and native session ids, prompt
delivery, Workflow start evidence, stop result, and zero unintended residual sessions.
Authentication-blocked command receipt is not reported as successful Workflow execution.
For Cursor CLI, live experiments must pass the exact non-FAST slug `grok-4.7-xhigh`, capture
the resulting `Grok 4.7 256K Extra High` footer without `Fast`, then run the prompt/reply proof.
Do not use native `/model` as a read-only probe: Cursor 2026.08.25 rewrites global picker config even
when the visible selection is unchanged.
