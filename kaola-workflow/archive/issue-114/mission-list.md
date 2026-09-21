# Issue #114: preflight receipt carries the adapter base fields (result/runtime/runtime_version/runtime_binary/detail)

- item: Confirm or correct the hypothesis — capture base_json in isolation for one platform and locate where the base fields are lost
  status: done
  dispatched: self — findings land inline in this item's result
  result: hypothesis CORRECTED. base_json is well-formed (PTY preflight carries result/runtime_version/detail incl. loopback=ensured). Cause: all ten manifests set default_transport acp, so kaola-tmux.sh exec's kaola-acp.py preflight before the preflight) case; adapter_preflight never runs on the default path.
- item: Fix scripts/kaola-tmux.sh so the preflight receipt carries the base fields; add one focused contract test (real adapter path) asserting result/runtime_version/detail; re-render skills/; CHANGELOG Unreleased entry
  status: done
  dispatched: self — lands as a commit on workflow/issue-114
  result: f39c602 — kaola-tmux.sh acp-preflight block + test_runner_preflight_receipt_carries_adapter_base_fields (test-acp-contract.py; FAIL before None != 'ready', OK after); 10 skills/ copies re-rendered; CHANGELOG Unreleased entry
- item: Readiness — render --check PASS and validate.sh 0 failed (both env conditions if the strip is needed); candidate committed on workflow/issue-114 for Host acceptance
  status: done
  dispatched: self — logs at /tmp/kpr114-validate-{inherited,stripped}.log
  result: render --check PASS; validate inherited env rc=1 (only the two known #115 cases: test-issue-73 dispatcher, zcode resolve fails-closed); validate with five Host vars stripped rc=0. Candidate f39c602 awaits Host acceptance; no finalize.
