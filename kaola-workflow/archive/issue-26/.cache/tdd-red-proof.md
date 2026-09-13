# Issue #26 TDD RED proof

Worktree: `/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/issue-26`
HEAD: `a3406d1` (design docs only; list/view/cursor/bin-install unimplemented)
Date: 2026-09-13

## Baseline that must stay green

```
cd /Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/issue-26
python3 tests/contract/test-acp-contract.py
```

Result: `Ran 14 tests in 17.445s` `OK` (ACP_RC=0). Mock `watch_projection` scenario is additive.

## New suite (registered in `scripts/validate.sh`)

```
python3 tests/contract/test-acp-watch-contract.py -v
```

Result: `Ran 8 tests in 4.005s` `FAILED (failures=7)` `EXIT:1`

| Test | Baseline result |
|---|---|
| `test_list_is_host_wide_and_omits_dead_holders` | FAIL: `list` parsed as platform; argparse exit 2, empty stdout |
| `test_view_matches_sample_key_set_and_types` | FAIL: `view` invalid command choice; empty stdout |
| `test_holder_restart_does_not_reuse_low_cursors` | FAIL: `view` invalid command (cursor reload unreached) |
| `test_view_runtime_facts_are_one_json_object` | FAIL: `view` invalid command; no `holder-lost`/`no-session` JSON |
| `test_acp_reference_names_human_list_and_view` | FAIL: `templates/references/acp.md.tmpl` has no `` `list` `` / `` `view` `` |
| `test_install_local_creates_owned_bin_symlinks` | FAIL: `$HOME/.local/bin/kaola-acp` is not a symlink |
| `test_install_refuses_foreign_bin_file` | FAIL: installer rc=0 and ignores a foreign `kaola-acp` file |
| `test_l0_send_wait_keys_stay_orchestrator_shaped` | PASS (preserve: no timeline/thinking_text/plan; observe options `{id,kind,label}`) |

## Files

- `tests/contract/test-acp-watch-contract.py` (new)
- `tests/contract/fixtures/kaola-acp-view-1.sample.json` (new; frozen sample)
- `tests/contract/mock-acp-agent.py` (`watch_projection` scenario)
- `scripts/validate.sh` (registers the new suite)

Production scripts/templates/skills were not edited for this proof.
