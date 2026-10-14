verdict: pass
validation_command: env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy ./scripts/validate.sh (full inventory, 1346s; single failure test-issue-162-upgrade-safety Seats exact-line repaired by 394ac518, then env -u ... python3 tests/contract/test-issue-162-upgrade-safety.py -> 27 tests OK on the repaired candidate; ./scripts/render-skills.py --check -> PASS)
validated_candidate_hash: 05c5f25148a481e7663552f11d5dae87e4122511892c37decd5da895950ac48a
