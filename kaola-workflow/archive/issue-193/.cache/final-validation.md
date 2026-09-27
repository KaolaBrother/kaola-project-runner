verdict: pass
validation_command: ./scripts/validate.sh rc=0 570s at 13750619 (installer logic/tests byte-identical since); at a94bbad9: ./scripts/render-skills.py --check && bash tests/contract/test-installer-runtimes.sh && bash tests/contract/test-installer-migration.sh && python3 tests/contract/test-issue-{148,118,130,168,147,49,50,52,73,74,88,86}-*.py (all rc=0)
validated_candidate_hash: a10ad031add6705b193bd4a0df57dbd9adead199855aa0b7c7df2d750ff05332
