# Trust-boundary review — `e8b91c6` vs `2ede8a8`

Focus: auto-permit, config/env skip overlay, ACP skip-all authorization confusion, terminal-control rejection, secrets.

Candidate: `e8b91c6d0750d4ae423ab345c9e320d2aee41b7f` (`docs: document OpenCode ACP has no skip-all; PTY --auto is the bypass`).
Diff surface: `CHANGELOG.md`, `README.md`, `platforms/opencode.yaml`, generated OpenCode Skill (`SKILL.md`, `references/acp.md`, `references/platform.md`, `scripts/platform.yaml`), `scripts/validate.sh`, `tests/contract/test-issue-24-opencode-pty-bypass.py`.
No change to `scripts/kaola-acp.py`, `scripts/kaola-acp-holder.py`, `scripts/kaola-tmux.sh`, `scripts/adapters/opencode.sh`, relay, or terminal-control paths (`git diff 2ede8a8..e8b91c6` on those files is empty).

Checks run (read-only): `python3 tests/contract/test-issue-24-opencode-pty-bypass.py` → 13 OK; `python3 scripts/render-skills.py --check` → PASS (6 Skills).

## Findings

None.

## Hunt (verified, no defect)

### Auto-answer of `session/request_permission`

Not introduced. Holder `on_agent_request` still queues `pending_permissions` and returns without `send_message` / `op_permit` (`scripts/kaola-acp-holder.py` ~537–555). Explicit `op_permit` remains a separate command (~850–878). New test `Issue24NoInventedSkipSubstitute.test_holder_does_not_auto_answer_request_permission` asserts that branch stays pending.

### Env / config overlay that silently allows tools

Not introduced. `ACP_SKIP_MODE` still omits `opencode` (`scripts/kaola-acp.py` 37–41). Default ACP start still has no `opencode)` `--mode` arm (`scripts/kaola-tmux.sh` 132–139). Adapter still writes only `agent.build.model` / `variant` into `OPENCODE_CONFIG_CONTENT` (`scripts/adapters/opencode.sh` 52–68). Diff contains no `OPENCODE_PERMISSION` and no `opencode.json` mutation. Contract tests lock those absences.

### Docs claiming ACP is skip-all when it is not

Candidate does the opposite. Agent-facing `acp_quirks` is `no ACP skip-all; PTY --auto via --transport pty is the bypass` (`platforms/opencode.yaml:24`, interpolated into generated `SKILL.md:14` and `references/acp.md:3`). `launch_summary` states default ACP has no skip-all and `configOptions.mode` is agent identity, not skip-all. README carve-out: OpenCode default ACP has no skip argv; `--auto` is PTY-only via `--transport pty`. CHANGELOG: no measured ACP skip; do not invent auto-permit or `OPENCODE_PERMISSION` skip. Default transport remains `acp`; `acp_command` remains `opencode acp` with no skip argv.

PTY `--mini --auto` is pre-existing adapter launch (`opencode.sh:42`), not a new skip. Naming it “the bypass” in quirks matches issue #24’s documented PTY path; it does not assert that default ACP start skips `session/request_permission` or user deny.

### Terminal-control rejection / payload fingerprinting

Untouched. README still states C0/C1 rejection before PTY write and send fingerprinting.

### Secrets

None in the diff. `acp_env_allowlist: OPENCODE_API_KEY` is unchanged parent fact, not a newly committed secret.

## Observation (not a defect)

`test-issue-24-opencode-pty-bypass.py` module docstring still describes the RED baseline (“empty `acp_quirks`”). That is stale commentary; tests themselves require non-empty documented quirks and pass on this SHA.

## Verdict

**PASS**
