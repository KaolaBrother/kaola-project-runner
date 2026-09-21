# Make ./scripts/validate.sh hermetic against Host-inherited KAOLA_* binding variables (#115)

- item: Scrub Host-binding KAOLA_* names in scripts/validate.sh before any suite runs, print removed names; CHANGELOG "## Unreleased" entry; prove inherited-env validate.sh passes 0 failed without manual stripping; render --check untouched
  status: done
  dispatched: self — lands on branch workflow/issue-115 in .kw/worktrees/issue-115
  result: commit abdd116 on workflow/issue-115 (scripts/validate.sh +15, CHANGELOG.md +13). Inherited-env ./scripts/validate.sh (6 KAOLA_* names present, no manual stripping) VALIDATE_EXIT=0; printed "validate: scrubbed inherited env: KAOLA_ACP_DISPATCHER KAOLA_ACP_HEARTBEAT_HOST KAOLA_ACP_HEARTBEAT_HOST_SOCKET KAOLA_CLAUDE_PROFILE_REQUIRED KAOLA_ZCODE_ENTRY KAOLA_ZCODE_NODE"; test_acp_start_under_a_dispatcher_passes_the_shell_to_the_acp_resolver ok; render-skills --check PASS, no generated changes. Awaiting Host acceptance before finalize.
