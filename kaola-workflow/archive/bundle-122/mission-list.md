# #122: entry-less platform as Host fails closed (host-entry-unsupported), per Yanlei ruling + Fable T1..T5

1. item: Implement fail-closed in scripts/kaola-acp.py — resolve_heartbeat_host row 4 (entry-less dispatcher) and an explicit KAOLA_ACP_HEARTBEAT_HOST naming an entry-less platform become typed refusal host-entry-unsupported (pre-spawn, no record); Host-named start on an entry-less platform refuses host-entry-unsupported; holder carrier refusal kept as depth; update the contract tests that pinned the old unbound row; add T1..T5 cases
   status: done
   dispatched: self — worktree .kw/worktrees/bundle-122, branch workflow/bundle-122
   result: commit beb8a04 — scripts/kaola-acp.py host_entry_unsupported(); resolve_heartbeat_host row 4 + explicit entry-less target refuse; command_start Host-named entry-less refusal first; tests updated (119 H1 skips entry-less, P5 + carrier test to refusal) and new test_issue_122_entryless_host_fails_closed (T1..T5)
2. item: Docs + gates — host-entry-matrix/zcode-host/api/main-Skill wording to the decided fail-closed rule, CHANGELOG, render --write/--check, validate.sh rc=0 (foreground), commit candidate
   status: done
   dispatched: self
   result: commit beb8a04 — host-entry-matrix (fail-closed paragraph, codex row), host-startup ref, docs/api.md, docs/zcode-host.md, CHANGELOG; render --check PASS; validate.sh rc=0 in 535 s, 0 FAIL, log kaola-workflow/bundle-122/validate.log
