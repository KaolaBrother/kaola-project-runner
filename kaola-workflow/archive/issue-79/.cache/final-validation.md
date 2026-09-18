verdict: pass
validation_command: ./scripts/render-skills.py --check && python3 tests/contract/test-issue-79-zcode-312.py && python3 tests/contract/test-zcode-acp-contract.py && python3 tests/contract/test-generated-skills.py && python3 tests/contract/test-issue-51-runner-integration.py && python3 tests/contract/test-zcode-host-contract.py && python3 tests/contract/test-zcode-heartbeat-contract.py && python3 tests/contract/test-issue-78-heredoc-deadlock.py && git diff --check
validated_candidate_hash: 173632eec450cff746de86a57a2c6798d7d2f9e4800fa223bcd76ad855b18631
