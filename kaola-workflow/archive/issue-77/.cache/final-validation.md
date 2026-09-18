verdict: pass
validation_command: ./scripts/render-skills.py --check && ./scripts/validate.sh && TMPDIR=$(mktemp -d) python3 tests/contract/test-issue-73-canonical-root.py
validated_candidate_hash: 7c11e85eae8b36914230bf3038f27fac654aa6c420bfa81384fc693e0b2ffb2d
