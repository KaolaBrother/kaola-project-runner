# Host-wide ACP list/view with frozen kaola-acp-list/1 and kaola-acp-view/1

- item: Pin focused acceptance tests that distinguish host-wide `list`, typed `view`, EventLog cursor reload, owned `$HOME/.local/bin` install, and unchanged L0 receipts, and fail on current main.
  status: done
  dispatched: tdd-guide on worktree `/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/issue-26`; tests, sample fixture, mock scenario, and `validate.sh` registration land there; RED proof log at `kaola-workflow/issue-26/.cache/tdd-red-proof.md`.
  result: tdd-guide died on a proxy error after mock+fixture only. Orchestrator finished inline. `python3 tests/contract/test-acp-watch-contract.py -v` → 8 tests, 7 FAIL, 1 PASS (L0 preserve). `test-acp-contract.py` 14 OK. Proof: `kaola-workflow/issue-26/.cache/tdd-red-proof.md`.

- item: Implement host-wide `kaola-acp list`, typed holder `view` projection, EventLog cursor reload from live plus rotated jsonl, `$HOME/.local/bin` owned `kaola-acp`/`kaola-acp-holder` symlinks, and Skill copy that humans use list/view; keep `templates/grok-golden/` frozen and make the acceptance suite green.
  status: done
  dispatched: implementer on worktree `/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/issue-26`; production change lands there; verification log at `kaola-workflow/issue-26/.cache/implement-verify.md`.
  result: Frozen `833fc86` on `workflow/issue-26`. Orchestrator re-ran watch 8 OK, acp-contract 14 OK, `render-skills.py --check` PASS, `validate.sh` VALIDATE_RC=0, `templates/grok-golden` empty. Evidence: `.cache/implement-verify.md`.

- item: Independently review the frozen candidate against issue #26 acceptance, trust boundary (no second ACP client on agent stdin, L0 keys unchanged), and test custody.
  status: done
  dispatched: three `code-reviewer` children on frozen `833fc86` in isolated worktrees; handbacks land at `kaola-workflow/issue-26/.cache/review-correctness.md`, `review-test-custody.md`, and `review-trust-boundary.md`.
  result: DEFECTS — trust-boundary PASS (0). Correctness: `view` can emit `holder-closed` outside `{holder-lost,holder-unreachable,no-session}`; `kaola-tmux.sh … view` is `unknown command` not `view-unsupported`. Test custody: `--since` only checks bools; rotation reload not independently distinguished; `assert_shape` skips null-typed fields. Evidence: `.cache/review-correctness.md`, `review-test-custody.md`, `review-trust-boundary.md`.

- item: Map view socket-close onto the frozen runtime fact codes, emit explicit `view-unsupported` from `kaola-tmux.sh`, and distinguish rotated-jsonl cursor reload plus `--since` cursor_gap in the watch tests.
  status: done
  dispatched: self on worktree `/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/issue-26`; change lands there.
  result: Frozen `ddb411c`. Watch suite 10 OK including accept-then-close and tmux `view-unsupported`; rotated max 800 distinguished; `--since 0` requires gap flags. `validate.sh` VALIDATE_RC=0; grok-golden empty. Evidence: `.cache/repair-verify.md`.
