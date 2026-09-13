# Correctness review — `833fc86` vs issue #26

Frozen candidate: `833fc86f249bb512bf98ff60c53a2bb313cfdb61`
(`feat: host-wide ACP list/view with frozen kaola-acp-view/1`).
Worktree was not modified; sources and tests were read from that commit
(temporary detached worktree `/tmp/review-833fc86`).

## Conclusion

**DEFECTS** (2 findings).

The stated happy-path acceptance for #26 holds under the contract tests and
direct probes: host-wide `list`, typed `kaola-acp-view/1`, plan full-replace,
per-`toolCallId` cards, view options `{optionId,name,kind}`, L0 key stability,
cursor reload across rotated jsonl, owned `~/.local/bin` symlinks, and the
three named runtime facts when those exact paths fire. Two error-surface
mismatches remain against `docs/acp-watch/list-view.md` (and the issue’s
closed set of view runtime codes).

## Tests run (candidate tree, no file changes)

- `python3 tests/contract/test-acp-watch-contract.py -v` — 8 tests, OK (4.778s)
- `python3 tests/contract/test-acp-contract.py` — 14 tests, OK (17.245s)
- `python3 scripts/render-skills.py --check` — PASS (6 Skills)

## Findings

### 1. `view` can emit `error.code=holder-closed`, which is outside the frozen set

- **File:line:** `scripts/kaola-acp.py:275` (produced) and `scripts/kaola-acp.py:229-231` (passed through as a view fact)
- **Concrete input:** `kaola-acp <platform> view --repo <git-root> --session <name>` when the short Unix socket **accepts** the CLI connection and then **closes without a JSON line**, while `record.json` still has a live `holder_pid`. That is the holder-dies-after-accept race; it was reproduced by unlinking the live sock and binding a dummy that `accept()`s then `close()`s immediately.
- **Observed stdout:**
  ```json
  {"error": {"code": "holder-closed", "message": "holder closed the connection"}, "schema": "kaola-acp-view/1"}
  ```
- **How established:** `socket_request` returns `{error:{code:"holder-closed",...}}` with no `schema` when `recv` yields empty. `command_view` remaps `holder-unreachable` onto the frozen set (and re-checks pid), but any other schemaless error is wrapped with **the raw code** (`view_error(str(err.get("code") or "holder-unreachable"), ...)`). Design / issue: runtime facts are one JSON object with `schema` and `error:{code,message}` and `code ∈ {holder-lost, holder-unreachable, no-session}`. Shape is right; code is not. The missing-socket path *does* emit `holder-unreachable` (probed: unlink sock, pid still alive).

### 2. PTY `kaola-tmux.sh … view` is `unknown command`, not explicit `view-unsupported`

- **File:line:** `scripts/kaola-tmux.sh:64`
- **Concrete input:** `bash scripts/kaola-tmux.sh grok view --repo <git-root> --session <name>`
- **Observed:** exit 1, empty stdout, stderr `kaola-tmux[grok]: unknown command: view`
- **How established:** ran that argv against the candidate. `view` is absent from the allowed command case, so dispatch dies before transport selection. `docs/acp-watch/list-view.md` Errors: if view is invoked via `kaola-tmux.sh` on PTY, emit explicit `view-unsupported` and do not fall back. There is no PTY fallback (good), but the frozen code is missing. Issue #26 also preserves “`kaola-tmux.sh` never dispatches `list`”; `list` is likewise rejected as unknown — that part matches.

## What the strongest refutation did *not* break

These were checked against the issue acceptance list and `docs/acp-watch/list-view.md` and did not fail:

| Claim | Evidence |
|---|---|
| `kaola-acp list` (no args) is host-wide; `--platform` / `--repo` only filter; dead holder omitted | `test_list_is_host_wide_and_omits_dead_holders`; implementation `command_list` + `sys.argv[1]=="list"` pre-parse |
| `view` is `kaola-acp-view/1`, key set/types vs `tests/contract/fixtures/kaola-acp-view-1.sample.json`; plan full-replace; unique `toolCallId` cards; options `{optionId,name,kind}` | `test_view_matches_sample_key_set_and_types`; probe after `watch_projection` showed plan `Read middleware` / `Patch redirect guard` (no stale merge) and options `allow_once` / `reject_once` |
| `--since C` only sets `cursor_gap`/`truncated` on the current snapshot | After a real turn, `--since 0` → `cursor_gap=true, truncated=true, event_cursor=10`; `--since 10` → both false; body still the compacted view |
| L0 `send --wait` has no `timeline` / `thinking_text` / `plan`; pending options stay `{id,kind,label}` | `test_l0_send_wait_keys_stay_orchestrator_shaped`; `test-acp-contract.py` still OK; `turn_receipt` unchanged |
| Same `record_dir` restart does not reuse cursor 1 on leftover high-cursor / rotated lines | `test_holder_restart_does_not_reuse_low_cursors`; `EventLog._restore_cursor` scans `.jsonl.3`…`.jsonl.1` then live |
| `$HOME/.local/bin/kaola-acp` (+ holder) owned symlink; refuse foreign file; uninstall owned only | `test_install_local_creates_owned_bin_symlinks`, `test_install_refuses_foreign_bin_file`; `install-local.sh` `bin_specs` |
| `no-session` / `holder-lost` one JSON object with `schema` + `error.{code,message}` | `test_view_runtime_facts_are_one_json_object` |
| `holder-unreachable` when sock missing and pid live | probe: `{"error":{"code":"holder-unreachable","message":"holder alive but socket path is absent"},"schema":"kaola-acp-view/1"}` |
| Skills name human `list`/`view`; grok-golden untouched | `test_acp_reference_names_human_list_and_view`; `833fc86` does not touch `templates/grok-golden/` |

## Observations (not counted as findings)

- `test_view_runtime_facts_are_one_json_object` never exercises `holder-unreachable` or the accept-then-close path; `assert_shape` does not check types when the sample value is JSON `null`.
- `EventLog.read_since` now walks rotated files as well as the live jsonl (needed for `oldest_cursor` / reload). That widens L2 `capture --since` versus the pre-#26 “live file only” fact; existing ACP contract tests still pass.
- Caps (thinking 8KiB / tool 32KiB / view 256KiB / timeline 200) set `truncated` and only actually slice the thinking tail, matching “超限只设 truncated，不硬门”.
