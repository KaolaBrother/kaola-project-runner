# Conventions

## Change boundary

The existing Grok contract is golden and live-proven. Do not rewrite, shorten, normalize, or
reinterpret its Skill, prompts, four modes, PR claim handoff, heartbeat, scheduler, or closing
protocol without explicit authorization and a new real Grok validation record. Other platforms
align to that contract; they do not redefine it.

## Source of truth

- Full lifecycle and prompts: `templates/grok-golden/`.
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
repositories and prove the Git top-level. Send prompts via tmux buffers, never interpolation or
`eval`. Do not use fuzzy tmux targets, basename-only ownership, process-name adoption, or global
tmux-server termination. Runtime identity requires the exact resolved binary at process argv[0] or
interpreter argv[1] plus the adapter's observed title/current-command predicate; captured output and
later argv text are activity/input evidence, not identity evidence.

## Tests and live evidence

Behavioral changes require baseline-failing acceptance. Offline tests use temporary repositories,
fake binaries, isolated homes, and unique tmux sessions. Real runtime tests are explicit and record
version, carrier proof, exact session, full prompt delivery, Workflow start evidence, stop result,
and zero unintended residual sessions. Authentication-blocked command receipt is not reported as
successful Workflow execution.
