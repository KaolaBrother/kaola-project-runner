verdict: pass
validation_command: env -u KAOLA_ZCODE_ENTRY -u KAOLA_ZCODE_NODE -u KAOLA_ACP_DISPATCHER -u KAOLA_ACP_HEARTBEAT_HOST ./scripts/render-skills.py --check && env -u KAOLA_ZCODE_ENTRY -u KAOLA_ZCODE_NODE -u KAOLA_ACP_DISPATCHER -u KAOLA_ACP_HEARTBEAT_HOST ./scripts/validate.sh
validated_candidate_hash: fc70d93330fb99004c56040c760d744f7a1fd1617c180510a39500bb9671f2f7
