verdict: pass
validation_command: ./scripts/render-skills.py --check && for s in test-issue-266-launch-broker.py test-issue-266-launch-broker-composed.py test-acp-sweep-contract.py test-issue-289-dead-holder-stop.py test-issue-348-backstop-sweep.py test-generated-skills.py test-issue-255-lifecycle-state.py; do ./scripts/validate.sh --suite $s || exit 1; done  # all pass on 33468603
validated_candidate_hash: 7cf9e9c2ddc36f4432f075fe21af8a30f08069ae04c47560e2ca022130819b0d
