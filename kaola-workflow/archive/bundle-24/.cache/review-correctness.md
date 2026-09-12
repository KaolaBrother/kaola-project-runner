# Correctness review — `e8b91c6`

Focus: issue #24 (keep default OpenCode ACP as `opencode acp` with no skip; document PTY `--auto` via `--transport pty` as the bypass; no invented auto-permit / `OPENCODE_PERMISSION`; `templates/grok-golden/` frozen; `validate.sh` green).

Checked: `git diff 2ede8a8..e8b91c6`; manifests/adapters/`kaola-tmux.sh`/`kaola-acp.py`/`kaola-acp-holder.py`; generated OpenCode Skill; `./scripts/render-skills.py --check`; `./scripts/validate.sh` (exit 0, including 13/13 issue-24 tests).

## Findings

### 1. Launch surface tells the Agent to start PTY, not default ACP

- `platforms/opencode.yaml:14` `launch_summary`:
  `Launch opencode <repo> --mini --auto via --transport pty. Default ACP has no skip-all; ...`
- Same string rendered as the entire `## Launch` body at `skills/opencode-kaola-project-runner/references/platform.md:28` (from `templates/references/platform.md.tmpl` `{{LAUNCH_SUMMARY}}`).
- Product default is still ACP: `platforms/opencode.yaml:21` `default_transport: "acp"`, `:22` `acp_command: "opencode acp"`. `scripts/kaola-tmux.sh:108` uses that manifest default when `--transport` is omitted. Generated `SKILL.md:40` start example has no `--transport`, so it stays ACP.

Concrete input: Agent follows Skill `references/platform.md` **Launch** (SKILL.md:115 points there for “launch/observation facts”) and runs `scripts/runtime-tmux.sh start --transport pty ...`. That is a caller override (`transport_reason=caller-override`), not `opencode acp`. `--mini --auto` only exist on the PTY adapter (`scripts/adapters/opencode.sh:42`).

Acceptance is: keep **default** ACP as `opencode acp` without skip, and **name PTY `--auto` via `--transport pty` as the bypass**. `acp_quirks` (`platforms/opencode.yaml:24`, SKILL.md:14, `references/acp.md:3`) does that. `launch_summary` does not: it is the Launch instruction and leads with the non-default transport as “Launch … via `--transport pty`”. Other platforms’ `launch_summary` describe default start (PTY argv + ACP skip on the default channel). OpenCode’s default channel cannot skip; presenting the bypass selector as Launch contradicts `default_transport: acp`.

### 2. New contract test refuses to cover that Launch line

`tests/contract/test-issue-24-opencode-pty-bypass.py:8-11` states the Agent-facing gap is empty `acp_quirks` and that “README/CHANGELOG/launch_summary notes are not this contract.”

The commit **does** change `launch_summary` (finding 1), but `validate.sh` cannot fail it. The 13 tests pin `acp_command` / `default_transport` / empty `ACP_SKIP_MODE` / PTY `--mini --auto` / quirks wording / no auto-permit / no `OPENCODE_PERMISSION` — not the Launch sentence the Agent is told to follow.

## What is not a defect

- Runtime default ACP is unchanged: no `opencode)` arm in `kaola-tmux.sh:135-139`, no `opencode` in `ACP_SKIP_MODE` (`scripts/kaola-acp.py:37-41`), holder `session/request_permission` stays pending (`kaola-acp-holder.py:537-555`).
- No `OPENCODE_PERMISSION` inject in start sources; adapter model env only sets `agent.build` model/variant.
- `templates/grok-golden/` has empty diff vs `2ede8a8`.
- `./scripts/validate.sh` green on this tree.

## Suspicion

CHANGELOG issue-22 bullet (`CHANGELOG.md:9-15`, not edited in this commit) still frames “default start … skip-all … on both ACP and PTY” and lists OpenCode PTY `--auto` in that set. Harmless next to the new #24 bullet; not introduced here.

## Conclusion

**DEFECTS.** Default ACP start is still `opencode acp` with no skip, golden is frozen, and `validate.sh` is green — but the generated Launch instruction steers `start` onto `--transport pty`, and the new tests are written so that cannot fail.
