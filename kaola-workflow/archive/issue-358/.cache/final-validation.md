verdict: fail
validation_command: env -u CLICOLOR -u CLICOLOR_FORCE -u FORCE_COLOR -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy -u KAOLA_ACP_DISPATCHER -u KAOLA_ZCODE_ENTRY -u KAOLA_ZCODE_NODE NO_COLOR=1 KAOLA_LAUNCH_BACKEND=direct stdbuf -oL -eL ./scripts/validate.sh
validated_candidate_hash: c83f4c65a1341d3a84814f14da2f593631a6f4d8d593e5f565495b9ab83fd0b6
