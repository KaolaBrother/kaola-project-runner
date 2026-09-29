verdict: pass
validation_command: python3 scripts/render-skills.py --check && python3 tests/contract/test-issue-118-seat-cap.py && git diff --check bdb21696..HEAD
validated_candidate_hash: f0cc1aee58074b31be609f5cec68e128a021c70e9dee60b1bcc4c4504b0c9e96
