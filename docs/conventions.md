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

Do not reintroduce direct `SIGSTOP` of the pane leader: tmux resumes it. Do not replace the tokenized
DECRQM parser fence with a sleep, double capture, plain DSR, control-mode pause, or tmux command-list
claim. Legacy-direct sessions are reporting-only until the user explicitly authorizes migration.

## Tests and live evidence

Behavioral changes require baseline-failing acceptance. Offline tests use temporary repositories,
fake binaries, isolated homes, unique tmux sessions, sanitized frame hashes, and public transport
commands. Relay changes additionally prove nonce-fence neutrality, child process-group quiescence,
escaped-descendant containment, lease/disconnect recovery, changed-observation reporting without
hardgate refusal, payload receipts, terminal-control outcomes, coordinate-invariant evidence,
truthful restoration, and zero residual sockets/processes.
Real runtime tests record version, relay/child/pane identity, snapshot, prompt
delivery, Workflow start evidence, stop result, and zero unintended residual sessions.
Authentication-blocked command receipt is not reported as successful Workflow execution.
For Cursor CLI, the validating Agent must explicitly select a non-FAST Cursor Grok 4.6 model through
the native `/model` UI, capture the selected row and post-selection footer without `Fast`, then run
the prompt/reply proof. This is a strict live-experiment protocol, not active Skill runtime policy.
