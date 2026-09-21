# Issue #116: zcode adapter recognises stopReason/stop_reason as an output-limit finish-reason key

1. item: Test first — fake zcode app-server turn.completed scenarios (stopReason / stop_reason = max_tokens; prose-quoting negative control; cancel-wins) + contract subtests in tests/contract/test-zcode-acp-contract.py; record the pre-fix failure
   status: done
   dispatched: self; lands in .kw/worktrees/bundle-116/tests/contract/{fake-zcode-app-server.py,test-zcode-acp-contract.py}
   result: scenarios completed_stop_{camel,snake,prose,cancel}; tests test_completed_stop_reason_key_reports_max_tokens, test_completed_prose_quoting_the_token_stays_end_turn, test_cancel_still_wins_over_a_completed_stop_reason. Pre-fix: camel+snake subtests FAIL ('end_turn' != 'max_tokens'), prose+cancel PASS
2. item: Add stopReason/stop_reason to OUTPUT_LIMIT_REASON_KEYS in scripts/kaola-zcode-acp.py; render --write; CHANGELOG ## Unreleased entry
   status: done
   dispatched: self; lands in worktree scripts/kaola-zcode-acp.py, skills/zcode-kaola-project-runner/scripts/kaola-zcode-acp.py (render --write), CHANGELOG.md
   result: keys added with #116 comment; render --write regenerated the one copy; render --check PASS; CHANGELOG ## Unreleased entry at top
3. item: Readiness — render --check PASS and ./scripts/validate.sh 0 failed (with #115 env strip if the known cases fail); candidate committed on workflow/bundle-116
   status: done
   dispatched: self; lands in kaola-workflow/bundle-116/kpr-116-validate-{inherited,stripped}.log and commit on workflow/bundle-116
   result: candidate 6a1eca6. render --check PASS. validate inherited env (KAOLA_ACP_DISPATCHER/HEARTBEAT_HOST(+_SOCKET)/ZCODE_ENTRY/NODE set): exit 1, only the known #115 cases (test-issue-73 heartbeat-host-conflict; test_resolve_runtime_fails_closed). validate with the #115 strip: exit 0, 0 failed. Awaiting Host acceptance before finalize.
