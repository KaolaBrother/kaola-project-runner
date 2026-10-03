# Issue #247 acceptance

Candidate: `fa607d18fe96332c192f8eb3ec41e22f8550704c`
Parent: `1a090852b8dd5400d426ae0c61a213e285cc9e60`
Accepted source commit, unamended: `caa84c382a1c199a053c4064680b0f6ff6e2b097`
Parent of that source commit, still: `c47daa1e8a1091eadadbca29aab6898695027083`

Outcome: accepted for this existing issue-247 run. Adapter
`@agentclientprotocol/codex-acp` 2.0.1 and child `@openai/codex` 0.160.0 stay
the accepted pair. Shared-root Skill installation is not required.

The rebased tip replays the accepted source onto current main. The only
content conflict was `scripts/validate.sh`, in `python_suites_all` and
`python_suites_b`. Both `test-issue-245-session-role.py` and
`test-issue-247-codex-child.py` are kept, with the #245 name immediately
before the #247 name. No other source file conflicted.
`caa84c382a1c199a053c4064680b0f6ff6e2b097` is not amended.

Evidence already recorded:

- Checkout start `codex-kaola-247-child160`, `CODEX_PATH` `/Users/ylmacstudio/.local/bin/codex`, mode read-only.
- Adapter `agentInfo` version 2.0.1. Launched child package `@openai/codex` 0.160.0.
- Marker `CODEX247_CHILD160_ACP_OK`, `stop_reason` `end_turn`, tool calls 0.
- Exact stop `residual_pids []`.
- `./scripts/validate.sh` from this worktree at `fa607d18fe96332c192f8eb3ec41e22f8550704c`, receipt `/tmp/kpr247-validate.log`, `EXIT:0`.
- `test_timeout_and_unknown_mutation_are_not_failed_or_returned` passed. Its expected reason remains `start-timeout`.

No release, tag, package publication, or shared-root install is part of this acceptance.
