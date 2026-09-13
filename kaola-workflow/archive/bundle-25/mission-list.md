# At-most-once ACP holder permit/cancel on one request_id

- item: Pin focused acceptance tests that distinguish two concurrent permits on one request_id (exactly one agent JSON-RPC result; loser gets a structured settled-fact), double cancel of the same pending id, and unchanged L0 receipts plus existing distinct-id concurrent permits; prove they fail on current main.
  status: done
  dispatched: tdd-guide on worktree `/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-25`; tests and any mock-scenario/validate.sh registration land there; RED proof log at `kaola-workflow/bundle-25/.cache/tdd-red-proof.md`.
  result: Frozen loser code `unknown-request`. Orchestrator re-ran `Issue25PermitLockTests` in the worktree: 4 tests, 2 FAIL (`test_concurrent_permit_same_request_id_at_most_once` two `permitted`; `test_concurrent_cancel_same_pending_id_at_most_once` two cancelled JSON-RPC results). Sequential + L0 PASS. Files: `tests/contract/test-acp-contract.py`, `tests/contract/hooks/sitecustomize.py`. Proof: `kaola-workflow/bundle-25/.cache/tdd-red-proof.md`.

- item: Implement permit/cancel/stop permission settlement under the same lock as prompt admission so each request_id writes at most one JSON-RPC result to agent stdin; keep templates/grok-golden frozen and make the acceptance suite green.
  status: done
  dispatched: implementer on worktree `/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-25`; production change lands there; verification log at `kaola-workflow/bundle-25/.cache/implement-verify.md`.
  result: Frozen `a76670c` on `workflow/bundle-25`. Orchestrator re-ran `Issue25PermitLockTests` 4 OK and distinct-id concurrent permit OK. Holder settles under `self.lock` via `_settle_pending_permission_locked`; loser `unknown-request`. Evidence: `.cache/implement-verify.md`. `templates/grok-golden` empty.

- item: Independently review the frozen candidate against issue #25 acceptance, trust boundary (exactly one agent-side result; L0 keys unchanged), and test custody.
  status: done
  dispatched: three `code-reviewer` children on frozen `a76670c` in isolated worktrees; handbacks land at `kaola-workflow/bundle-25/.cache/review-correctness.md`, `review-test-custody.md`, and `review-trust-boundary.md`.
  result: PASS (0 findings) on all three cuts. Orchestrator read the review files, not the prose. Inbound `pending_permissions` mutation without `Holder.lock` is a labeled suspicion, not a double-write. Evidence: `.cache/review-correctness.md`, `review-test-custody.md`, `review-trust-boundary.md`.
