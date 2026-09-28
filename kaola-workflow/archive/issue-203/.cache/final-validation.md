verdict: pass
validation_command: (cd tests/contract && python3 -m unittest test-acp-contract.Issue203StartEvidenceTests test-acp-contract.Issue34ModelSelectionAcpTests && python3 -m unittest test-issue-130-pty-retired.ModelPolicyOnAcp) && ./scripts/render-skills.py --check
validated_candidate_hash: 1e2bb7e1cc6698530718d3ba91ba6d2926636fa8b99dbea713c04b5b92c2f156
