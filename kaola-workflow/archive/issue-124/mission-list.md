# #124 grok: record the session's actual CLI version at start and re-verify the ACP contract on 1.0.40

Forge note: the brief cites "two comments (decision record + Fable review)" on #124; the forge
returns zero comments (gh api issues/124/comments, 2026-09-21), so the issue body is the design
and acceptance source.

1. item: Implement the start-time CLI version fact for grok (record.json + start receipt, no gate) with a contract test in an existing suite; render sync
   status: done
   dispatched: self; output lands on branch workflow/issue-124 in .kw/worktrees/issue-124
   result: commit 14a329f (scripts/kaola-acp.py cli_version_fact + CLI_VERSION_PLATFORMS={grok}; holder --cli-version -> record/state cli_version; test-acp-contract.py test_start_records_launched_cli_version_without_gating red on baseline, green on candidate; render --check PASS)
2. item: Live ACP smoke on local grok 1.0.40 (start/send/read/cancel/stop) under session-scoped HTTP(S)_PROXY; archive evidence under kaola-workflow/issue-124/evidence/
   status: done
   dispatched: self; live run of candidate 14a329f scripts against /tmp scratch repo, record root /tmp/kpr-i124-smoke/records; evidence lands in kaola-workflow/issue-124/evidence/grok-1.0.40-acp-smoke.md (+ copied events.jsonl/record.json)
   result: PASS — kaola-workflow/issue-124/evidence/grok-1.0.40-acp-smoke.md (+ raw dir): end_turn, cancelled, process_exited code 0, residual_pids [], cli_version recorded live; steering -32601 unchanged
3. item: Update platforms/grok.yaml acp_verified_versions + steering_summary to the measured version; render --write/--check; validate.sh rc=0 with log archived
   status: done
   dispatched: self; manifest edit on workflow/issue-124; validate log lands in kaola-workflow/issue-124/evidence/validate.log
   result: commit 970f546 (grok.yaml cli=1.0.40 + steering_summary; generated grok platform.yaml/steering.md; docs/api.md + CHANGELOG); render --check PASS; validate.sh rc=0 on 970f546 content -> evidence/validate.log (test-acp-contract 48 tests OK)
4. item: Delivery report (diff summary, evidence, acceptance mapping, doc-impact) for Host acceptance; no finalize
   status: done
   dispatched: self; report lands in the conversation reply to the Host
   result: delivered in the session reply 2026-09-21; candidate tip 970f546 awaits Host acceptance
