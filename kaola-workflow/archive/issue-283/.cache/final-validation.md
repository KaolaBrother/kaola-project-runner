verdict: pass
validation_command: direct sandboxed suite runs at c3a0e4f7 (validate.sh --suite is blocked by the pre-existing render-check pin finding): python3 tests/contract/test-issue-73-canonical-root.py (31 OK); python3 tests/contract/test-acp-holder-continue.py (29 OK); earlier at 8c94c3a4 (same scripts/tests bytes): test-acp-contract.py 85 OK, test-issue-255-lifecycle-state.py 128 OK, test-issue-50-runner-integration.py 6/7 (only the render --check assertion fails)
validated_candidate_hash: c9854753b28057a72904a58175b332579eb5de463dc63c769d2d82288a6906a0
