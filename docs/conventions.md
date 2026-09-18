# Conventions

## Change boundary

The existing Grok Workflow contract is golden and live-proven historical evidence. Do not rewrite its
bytes. It is not the active Runner authority: all nine worker Skills use the shared communication-only
template and do not impose task modes, prompts, PR handoff, heartbeat, scheduler, or closing policy.
Project-level heartbeat, acceptance, Workflow merge preference with conditional open-PR priority, idle-session stop, and end-of-run close-out live in the generated main Skill `kaola-project-runner`.

## Source of truth

- Active nine-platform worker Skill: `templates/SKILL.md.tmpl`.
- Main orchestrator Skill: `templates/orchestrator/` (English `SKILL.md.tmpl`; not a platform
  manifest or adapter).
- One canonical Skill system, host adapters for packaging: every host output is derived by
  `render-skills.py` from the orchestrator template, the worker template, the platform manifests,
  and their canonical references. A host adapter (the delimited "Host adapter" section of the
  renderer) may add only host-specific packaging — reference expansion, path hints, account form,
  fingerprints, install steps — never a second hand-written body and never scheduling, safety, or
  transport semantics. Products are owned by `--write`, rejected on drift by `--check` and the
  host verifier, and updated automatically when a canonical source changes.
- Grok Bot host bundle: `hosts/grok-bot/` rendered by the `grok-bot` host adapter (inputs:
  `GROK_BOT_ADAPTER_INPUTS` = `templates/grok-bot/` only) — one thin bridge Skill
  `kaola-project-runner.md`, `bridge.json`, and `INSTALL.md`. The bridge carries the accepted
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
- Shared evidence-first transport guidance: `templates/references/transport.md.tmpl` plus exact reversible
  renderer overlays; never broad-replace golden prose.
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
unbounded terminal history, on PTY and ACP alike; an over-budget receipt keeps its newest part
and names the rest in a `truncated` block with counts and sha256 (`capture --full` is the
explicit, requested exception). Host adapters may not flatten,
concatenate, eagerly preload, or duplicate canonical Skill bodies for packaging convenience.
Every platform adapter and host declares measurable byte budgets for discovery, activation,
selected-worker increment, references, and tool outputs in `templates/budgets.json`;
`render-skills.py --check` and the contract tests fail when a budget or a loading boundary
regresses. A bridge host (Grok Bot) binds its execution target first and loads the canonical
Skills from a verified checkout on that target; nothing is copied into the account.

## Shell safety

Use macOS-compatible Bash with `set -euo pipefail`. Platform IDs use fixed dispatch. Canonicalize
repositories and prove the Git top-level. Send prompt bytes through the attested relay protocol,
never interpolation or `eval`. Do not use fuzzy tmux targets, basename-only ownership, process-name
adoption, raw tmux input as a guarded-action substitute, or global tmux-server termination. Runtime
identity requires the exact relay pane leader plus exact nested runtime child path/argv/PID/PGID and
adapter TUI evidence. Reject terminal controls before child PTY writes; LF/TAB require attested
bracketed paste. Raw frames, coordinates, captured output, editor/approval/activity labels, worker
counts, and later argv text are evidence for the controlling agent, not Runner semantic authority.
Generic send/stop may not branch on those advisory fields.

`scripts/kaola-tmux.sh` carries no here-document and no here-string. Bash writes a heredoc body up
to 4096 bytes into a pipe from the forked child before `exec`, so that one process holds both ends
and nothing drains it; macOS hands out 512-byte pipes under pipe-KVA pressure, and a larger body
then blocks in `write()` forever, leaving a child that wears the script's argv and outlives a
SIGKILL aimed at its parent (Issue #78). Pass Python programs with `-c` and feed `read` from a
process substitution.

Each platform Skill must teach the same measured loop: start, observe/capture, let the Agent decide,
transfer the chosen prompt or key, observe/capture the response, and stop the exact session when the
Agent chooses. Workflow/Git/forge verification occurs only when the Agent chose a Workflow task.
Snapshot changes and retained drafts are evidence, never Skill-owned policy gates. The same Skills
recommend — never require — stopping owned runtime once delegated work is delivered, keeping
already-available resume facts (native session ID is not the Runner session name); `stop` never
deletes history, and resume stays the Agent's choice among `--resume`, `--continue`, or a fresh
session.

Model mismatch, unreadable actual-model evidence, login failures, and resume behavior are likewise
facts for the controlling Agent. Never turn them into a start/send/observe/stop gate or rewrite the
Agent-selected model literal.

Normal observe/send/answer/key/stop paths must not stop the child, disable pane input, acquire a lease,
or run the tokenized DECRQM compatibility fence. Legacy relays are reporting-only for mutation until
the Agent explicitly chooses an exact-session restart.

## Canonical project root and Workflow child worktrees

Ordinary Workflow-backed work starts the worker at the consuming project's canonical project root
and asks that runtime to invoke `workflow-next` in-session. The worker's Workflow owns the child
worktree. Linked-worktree starts and existing-run recovery are Agent decisions, not transport
gates; PTY and ACP share that authority. Do not add a `.kw/worktrees` refusal to adapters or
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
nine worker Skills gain no classifier, the 1-80 `--session` syntax is the only validator, no
registry, daemon, or Workflow state field is added, and a running session is never renamed or
restarted to adopt the rule. Whether any consumer displays issue-run progress from these names
is outside this repository and is not verified here.

## Tests and live evidence

Behavioral changes require baseline-failing acceptance. Offline tests use temporary repositories,
fake binaries, isolated homes, unique tmux sessions, sanitized frame hashes, and public transport
commands. Relay changes additionally prove live observation without suspension, direct long-prompt
transfer, escaped-descendant non-blocking plus exact-stop cleanup, payload receipts, terminal-control
outcomes, coordinate-invariant evidence, legacy protocol compatibility, and zero residual
sockets/processes.
Real runtime tests record version, relay/child/pane identity, snapshot, prompt
delivery, Workflow start evidence, stop result, and zero unintended residual sessions.
Authentication-blocked command receipt is not reported as successful Workflow execution.
For Cursor CLI, live experiments must pass the exact non-FAST slug `cursor-grok-4.6-xhigh`, capture
the resulting `Cursor Grok 4.6 Extra High` footer without `Fast`, then run the prompt/reply proof.
Do not use native `/model` as a read-only probe: Cursor 2026.08.25 rewrites global picker config even
when the visible selection is unchanged.
