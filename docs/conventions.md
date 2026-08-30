# Conventions

## Change boundary

The existing Grok contract is golden and live-proven. Do not rewrite, shorten, normalize, or
reinterpret its Skill, prompts, four modes, PR claim handoff, heartbeat, scheduler, or closing
protocol without explicit authorization and a new real Grok validation record. Other platforms
align to that contract; they do not redefine it.

## Source of truth

- Full lifecycle and prompts: `templates/grok-golden/`.
- Shared guarded transport guidance: `templates/references/transport.md.tmpl` plus exact reversible
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
bracketed paste. Captured output, activity prose, and later argv text are evidence, not authority.

Do not reintroduce direct `SIGSTOP` of the pane leader: tmux resumes it. Do not replace the tokenized
DECRQM parser fence with a sleep, double capture, plain DSR, control-mode pause, or tmux command-list
claim. Legacy-direct sessions are reporting-only until the user explicitly authorizes migration.

## Tests and live evidence

Behavioral changes require baseline-failing acceptance. Offline tests use temporary repositories,
fake binaries, isolated homes, unique tmux sessions, sanitized frame hashes, and public guarded
commands. Relay changes additionally prove nonce-fence neutrality, child process-group quiescence,
escaped-descendant containment, lease/disconnect recovery, byte-revision staleness, prepared-surface
revalidation, terminal-control refusal, placeholder cursor evidence, and zero residual sockets/processes.
Real runtime tests record version, relay/child/pane identity, snapshot, prompt
delivery, Workflow start evidence, stop result, and zero unintended residual sessions.
Authentication-blocked command receipt is not reported as successful Workflow execution.
