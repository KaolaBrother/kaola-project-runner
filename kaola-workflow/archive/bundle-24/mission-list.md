# Default OpenCode ACP start does not hang send --wait on unanswered session/request_permission

- item: Measure whether OpenCode ACP exposes any skip-all permission knob (CLI flags, env, config, ACP initialize) and record the exact commands and outputs.
  status: done
  dispatched: investigator (live CLI/config/ACP) and knowledge-lookup (vendor docs) on main checkout; handbacks land at `kaola-workflow/bundle-24/.cache/measure-opencode-acp-skip.md` and `kaola-workflow/bundle-24/.cache/vendor-opencode-acp-skip.md`.
  result: `measured_skip_exists: no` for OpenCode 1.18.29. ACP argv/`configOptions` have no skip-all; `opencode acp --auto` exits 1; `opencode --auto acp` is a project path; `mode=yolo|auto|bypass` returns -32602. Vendor docs and anomalyco/opencode#47918 agree. TUI/PTY `--auto` remains. `permission: allow` / `OPENCODE_PERMISSION` is config overlay, not an ACP start knob. Evidence: `.cache/measure-opencode-acp-skip.md`, `.cache/vendor-opencode-acp-skip.md`.

- item: Pin focused acceptance tests that distinguish a measured OpenCode ACP skip from an explicit documented PTY `--auto` bypass, and fail on invented process-time auto-permit or a default ACP start that still claims skip-all.
  status: done
  dispatched: tdd-guide on worktree `/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-24`; tests and registration land in that worktree; RED proof log at `kaola-workflow/bundle-24/.cache/tdd-red-proof.md`.
  result: `tests/contract/test-issue-24-opencode-pty-bypass.py` registered in `scripts/validate.sh`. Orchestrator re-ran: 13 tests, 4 FAIL (empty `acp_quirks` / generated Skill ACP surface), 9 PASS (keep ACP without skip, PTY `--mini --auto`, no auto-permit, no `OPENCODE_PERMISSION`). RED proof: `.cache/tdd-red-proof.md`.

- item: Make default OpenCode ACP start satisfy issue #24 using only a measured skip, or keep ACP without skip and document PTY `--auto` as the bypass path; keep `templates/grok-golden/` frozen and `validate.sh` green.
  status: done
  dispatched: implementer on worktree `/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-24`; production change lands there; verification log at `kaola-workflow/bundle-24/.cache/implement-verify.md`.
  result: Frozen `e8b91c6` on `workflow/bundle-24`. `acp_quirks`: `no ACP skip-all; PTY --auto via --transport pty is the bypass`. Orchestrator re-ran `test-issue-24` 13 OK, `render-skills.py --check` PASS, `validate.sh` VALIDATE_RC=0, `templates/grok-golden` empty. Evidence: `.cache/implement-verify.md`.

- item: Independently review the frozen candidate against issue #24 acceptance, trust boundary (no invented auto-permit, prompts still literal), and test custody.
  status: done
  dispatched: three `code-reviewer` children on frozen `e8b91c6` in isolated worktrees; handbacks land at `kaola-workflow/bundle-24/.cache/review-correctness.md`, `review-test-custody.md`, and `review-trust-boundary.md`.
  result: DEFECTS — trust-boundary PASS; test-custody PASS. Correctness: `launch_summary` / generated `references/platform.md` Launch leads with `via --transport pty` while `default_transport` remains `acp`, steering start off default ACP. Tests explicitly exclude `launch_summary`. Evidence: `.cache/review-correctness.md`, `review-test-custody.md`, `review-trust-boundary.md`.

- item: Correct OpenCode `launch_summary` so default ACP remains the launch instruction and PTY `--auto` via `--transport pty` is named only as the bypass, then re-render and re-validate.
  status: done
  dispatched: self on worktree `/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-24`; change lands there.
  result: Frozen `4b031ad`. First Launch sentence is `Launch opencode <repo> --mini --auto`; bypass named later as `PTY --auto via --transport pty`. New test `test_launch_summary_does_not_steer_default_start_onto_pty` was RED on `e8b91c6` text then 14 OK. `validate.sh` VALIDATE_RC=0; grok-golden empty.
