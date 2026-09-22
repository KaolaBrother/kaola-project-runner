# Documentation docking — issue-132 (candidate c034596, tree ac811be)

| File | Status | Evidence |
|---|---|---|
| README.md | updated | "One project, one Project Runner Agent" block: one live Host per root, host-exists, identity check, exact-stop + proven gone, sweep= line, mismatch reported |
| CHANGELOG.md | updated | Unreleased entry "One live Host per repo…" (above the #130 entry; merge kept both) |
| docs/api.md | updated | list `--include-dead` + row fields (identity/host_class/dispatcher/heartbeat_host); host-exists receipt (existing_host, identity, argv, answering_holder_instance_id); session-exists identity; stop --force argv anchor / answering_socket / pid_reused / agent_started sweep; probe bounds |
| docs/zcode-host.md | updated | host-exists paragraph after main-skill-build-skew |
| docs/acp-watch/list-view.md | updated | `--include-dead` opt-in; row keys identity, host_class, dispatcher, heartbeat_host(_known) |
| skills/kaola-delegator/SKILL.md, references/handoff.md | rendered from templates | One Host rule, Recover steps 1–3, sweep= line, proven gone |
| skills/kaola-project-runner/SKILL.md, references/host-startup.md, references/zcode-host-dispatch.md | rendered from templates | host-exists, repo sweep section/table, identity-verified seat count |
| heartbeat-skeleton.md | no change | C11 optional per design; 3 B headroom at freeze |
| AGENTS.md | no change | project facts unchanged; "no registry/lock/pointer file" rule already stated and honored |

Known wording nuance, disclosed not changed (Host ruling): docs/api.md "epoch seconds, so time zones do not matter" is slightly absolute for the repeated-DST-hour cross-TZ case (review L4).

DOCKED
