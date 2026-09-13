# ACP watch local follow stream on the holder socket

- item: Pin focused acceptance tests that distinguish holder `follow` NDJSON (snapshot then increasing-cursor deltas), two followers seeing the same `tool_call`, follow-FD write of `prompt`/`permit` rejected with no extra agent-stdin ACP frames, a third socket still able to `permit`, slow follower `follow-dropped` without pausing agent stdio, `process_exited` then `eof`, holder-lost as an error line, and killing the follow CLI leaving holder/agent alive; prove they fail on current main.
  status: done
  dispatched: tdd-guide on worktree `/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-27`; tests, any mock scenario, and `validate.sh` registration land there; RED proof log at `/Users/ylpromax5/Workspace/kaola-project-runner/kaola-workflow/bundle-27/.cache/tdd-red-proof.md`.
  result: Orchestrator re-ran `python3 tests/contract/test-acp-follow-contract.py -v` in the worktree → 11 tests, 11 FAIL, FOLLOW_EXIT=1 (CLI `invalid choice: 'follow'`; holder `unknown-op`). Watch suite still 10 OK. Files: `tests/contract/test-acp-follow-contract.py`, `tests/contract/mock-acp-agent.py` (`follow_flood` + `inbound_frame`), `scripts/validate.sh`. Proof: `kaola-workflow/bundle-27/.cache/tdd-red-proof.md`.

- item: Implement holder `op_follow` plus CLI `follow` (`--since`, optional `--format text`), read-only after the first follow op, heartbeats carrying full `pending_permissions` and `mutation_status`, per-follower queue cap 256, Skill copy that names local follow, keep `templates/grok-golden/` frozen, and make the acceptance suite green.
  status: done
  dispatched: implementer on worktree `/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-27`; production change lands there; verification log at `/Users/ylpromax5/Workspace/kaola-project-runner/kaola-workflow/bundle-27/.cache/implement-verify.md`.
  result: Orchestrator re-ran follow 11 OK, watch 10 OK, acp-contract 18 OK, `render-skills.py --check` PASS. grok-golden empty. Evidence: `.cache/implement-verify.md`. Dirty worktree on `workflow/bundle-27` (not committed).

- item: Independently review the frozen candidate against issue #27 acceptance, trust boundary (follow never writes ACP JSON-RPC to agent stdin; exclusive agent stdio; L0 keys unchanged), and test custody.
  status: done
  dispatched: three `code-reviewer` children on dirty worktree `/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-27`; handbacks land at `/Users/ylpromax5/Workspace/kaola-project-runner/kaola-workflow/bundle-27/.cache/review-correctness.md`, `review-test-custody.md`, and `review-trust-boundary.md`.
  result: DEFECTS — trust-boundary PASS (0). Test custody PASS (0). Correctness: drop uses sticky 50ms-block plus lifetime `produced` instead of queue depth 256; `tool_call`/plan/mode/usage set unused `follow_dirty` and do not emit deltas. Evidence: `.cache/review-correctness.md`, `review-test-custody.md`, `review-trust-boundary.md`.

- item: Drop a follower only when its per-connection queue exceeds 256 lines, and emit cursor deltas for every view-changing update including `tool_call` without a later permission card.
  status: done
  dispatched: self on worktree `/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-27`; change lands there.
  result: Queue-only drop; apply-then-append then fanout every session/update. Follow 12 OK, watch 10 OK, acp 18 OK, `validate.sh` VALIDATE:0, grok-golden empty. Evidence: `.cache/repair-verify.md`.
