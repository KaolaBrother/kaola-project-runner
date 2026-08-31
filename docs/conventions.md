# Conventions

## Change boundary

The existing Grok Workflow contract is golden and live-proven historical evidence. Do not rewrite its
bytes. It is not the active Runner authority: all five active Skills use the shared communication-only
template and do not impose task modes, prompts, PR handoff, heartbeat, scheduler, or closing policy.

## Source of truth

- Active five-platform Skill: `templates/SKILL.md.tmpl`.
- Frozen historical Workflow lifecycle and prompts: `templates/grok-golden/`.
- Shared evidence-first transport guidance: `templates/references/transport.md.tmpl` plus exact reversible
  renderer overlays; never broad-replace golden prose.
- Fixed runtime facts: one `platforms/*.yaml` manifest.
- Executable differences: one `scripts/adapters/*.sh` adapter.
- `skills/`: generated, committed output; never hand-edit it.
- Workflow commands and roles: the Kaola Workflow distribution, not this repository.

After an allowed source change:

```bash
./scripts/render-skills.py --write
./scripts/validate.sh
```

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

Each platform Skill must teach the same measured loop: start, observe/capture, let the Agent decide,
transfer the chosen prompt or key, observe/capture the response, and stop the exact session when the
Agent chooses. Workflow/Git/forge verification occurs only when the Agent chose a Workflow task.
Snapshot changes and retained drafts are evidence, never Skill-owned policy gates.

Model mismatch, unreadable actual-model evidence, login failures, and resume behavior are likewise
facts for the controlling Agent. Never turn them into a start/send/observe/stop gate or rewrite the
Agent-selected model literal.

Normal observe/send/answer/key/stop paths must not stop the child, disable pane input, acquire a lease,
or run the tokenized DECRQM compatibility fence. Legacy relays are reporting-only for mutation until
the Agent explicitly chooses an exact-session restart.

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
