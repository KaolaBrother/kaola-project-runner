# Issue #26 implementer verification

Worktree: `/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/issue-26`
Branch: `workflow/issue-26`
Date: 2026-09-13

All commands run from the worktree. No commit. `templates/grok-golden/` untouched.

## 1. Watch contract

```
cd /Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/issue-26
python3 scripts/render-skills.py --write
python3 tests/contract/test-acp-watch-contract.py -v
```

`render-skills.py --write` was required before the watch suite so generated `skills/*/references/acp.md` contains the human `` `list` `` / `` `view` `` names the template test also checks.

Result:

```
render-skills: WROTE (6 Skills)
test_acp_reference_names_human_list_and_view ... ok
test_holder_restart_does_not_reuse_low_cursors ... ok
test_l0_send_wait_keys_stay_orchestrator_shaped ... ok
test_list_is_host_wide_and_omits_dead_holders ... ok
test_view_matches_sample_key_set_and_types ... ok
test_view_runtime_facts_are_one_json_object ... ok
test_install_local_creates_owned_bin_symlinks ... ok
test_install_refuses_foreign_bin_file ... ok

Ran 8 tests in 4.088s
OK
```

Watch suite: 8 tests, 0 failures.

## 2. Existing ACP contract (must stay green)

```
python3 tests/contract/test-acp-contract.py
```

Result:

```
Ran 14 tests in 17.074s
OK
ACP_CONTRACT_RC=0
```

## 3. Render write + check

```
python3 scripts/render-skills.py --write && python3 scripts/render-skills.py --check
```

Result:

```
render-skills: WROTE (6 Skills)
render-skills: PASS (6 Skills)
RENDER_RC=0
```

## 4. Full validate.sh

```
./scripts/validate.sh
```

Result (tail of the run):

```
render-skills: PASS (6 Skills)
Skill is valid!  (x6)
Ran 7 tests in 0.033s OK
Ran 5 tests in 0.001s OK
Ran 31 tests in 0.426s OK
Ran 14 tests in 17.104s OK
Ran 8 tests in 4.154s OK
Ran 4 tests in 0.002s OK
generated Skill acceptance: PASS
Ran 14 tests in 0.017s OK
VALIDATE_RC=0
```

## 5. Frozen golden tree

```
git diff --stat templates/grok-golden
```

Result: empty stdout, `GOLDEN_DIFF_RC=0`.

## Not run

- Live tmux / live CLI UAT per platform (not claimed; contract suite is offline mock).
- No commit.

## Production files changed (worktree)

- `scripts/kaola-acp.py` — host-wide `list`, typed `view`, view runtime-fact JSON
- `scripts/kaola-acp-holder.py` — ViewProjection, `op_view`, EventLog cursor reload from live+rotated jsonl
- `scripts/install-local.sh` — owned `$HOME/.local/bin` symlinks; refuse foreign; uninstall owned only
- `templates/references/acp.md.tmpl` — human `` `list` `` / `` `view` ``
- `skills/*` — regenerated via `render-skills.py --write` (not hand-edited)
