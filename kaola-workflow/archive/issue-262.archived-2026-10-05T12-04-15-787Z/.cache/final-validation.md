verdict: pass
validation_command: python3 scripts/render-skills.py --check && python3 tests/contract/test-generated-skills.py && python3 tests/contract/test-progressive-disclosure.py && python3 tests/contract/test-issue-74-kaola-delegator.py && python3 tests/contract/test-issue-86-delegator-quota.py && python3 tests/contract/test-issue-255-lifecycle-state.py && python3 tests/contract/test-issue-244-dispatch.py && python3 tests/contract/test-issue-187-delegator-any-host.py GeneratedDelegator
validated_candidate_hash: ba47327f1d536035b6f309749e4881e25c523eb3b28380f9830ce34fb8472de7
