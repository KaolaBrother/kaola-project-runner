verdict: pass
validation_command: /opt/homebrew/bin/bash ./scripts/validate.sh --suite test-zcode-heartbeat-contract.py --suite test-issue-388-role-carrier.py --suite test-issue-393-cwd-carrier.py; PATH=/opt/homebrew/bin:$PATH /opt/homebrew/bin/bash ./scripts/validate.sh --suite test-issue-388-role-carrier.py; PATH=/opt/homebrew/bin:$PATH /opt/homebrew/bin/bash ./scripts/validate.sh --suite test-issue-76-permission-wake.py; ./scripts/render-skills.py --write; ./scripts/render-skills.py --check
validated_candidate_hash: d08ee12fa970248a914fb34d46c1d74f1df8699375eb9dc80070de6312c23904
