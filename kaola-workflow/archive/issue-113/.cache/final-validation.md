verdict: pass
validation_command: ./scripts/render-skills.py --check && env -u KAOLA_ZCODE_ENTRY -u KAOLA_ZCODE_NODE -u KAOLA_ACP_DISPATCHER -u KAOLA_ACP_HEARTBEAT_HOST -u KAOLA_ACP_HEARTBEAT_HOST_SOCKET ./scripts/validate.sh  # 2026-09-21 on 7c237c5: render PASS budgets OK; VALIDATE_EXIT=0, 0 FAILED
validated_candidate_hash: 36ec2f623abc9426d959a5b1c4a12bc80831811d6dd93502276c86bce1a735a9
