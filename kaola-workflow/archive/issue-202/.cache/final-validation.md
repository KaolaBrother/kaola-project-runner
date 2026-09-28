verdict: pass
validation_command: ./scripts/render-skills.py --check && for f in tests/contract/test-issue-187-delegator-any-host.py tests/contract/test-issue-74-kaola-delegator.py tests/contract/test-issue-65-steering.py tests/contract/test-issue-52-workflow-worktree.py tests/contract/test-runner-v2.py tests/contract/test-issue-111-model-tiers.py tests/contract/test-issue-94-zcode-native-skill-entry.py tests/contract/test-progressive-disclosure.py; do python3 "$f" || exit 1; done
validated_candidate_hash: 662278977482bad6833725ad2fb2084af1fb85fc9fe3da271ae6fbedde89e80b
