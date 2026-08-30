verdict: pass
validation_command: python3 scripts/render-skills.py --write && python3 scripts/render-skills.py --check && git diff --check && ./scripts/validate.sh
validated_candidate_hash: a5230f277f1aec2460324170756bca69414a1f8476ae9fc9c1ad72b01f86bd46
