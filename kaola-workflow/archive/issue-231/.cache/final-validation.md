verdict: pass
validation_command: ./scripts/render-skills.py --check && python3 tests/contract/test-issue-98-dsh-acp.py && python3 tests/contract/test-generated-skills.py && python3 tests/contract/test-progressive-disclosure.py && python3 tests/contract/test-issue-218-preset-ids.py (affected checks at merge 82d1f02f; test-issue-118-seat-cap.py 1 failure pre-existing on main b0cf2652, unrelated)
validated_candidate_hash: 34297d7c463c7e600fc358eac86393e6013ebbbcb771199d184006fb0d0d9a38
