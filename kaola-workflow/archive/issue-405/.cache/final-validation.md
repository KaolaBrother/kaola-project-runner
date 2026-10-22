verdict: pass
validation_command: ./scripts/validate.sh --suite test-issue-76-permission-wake.py --suite test-issue-341-agent-initiated-turn.py --suite test-issue-255-lifecycle-state.py --suite test-zcode-heartbeat-contract.py && python3 negctl-76.py && python3 negctl-341.py (never-true predicates fail at the stated budget); full inventory ./scripts/validate.sh green on 42fe48ff for the surface untouched by the repair
validated_candidate_hash: 8d149c39d7a0b99f4acfe0239b06a0a966fb06f4
