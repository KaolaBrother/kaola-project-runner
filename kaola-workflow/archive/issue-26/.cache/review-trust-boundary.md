# Trust-boundary review — frozen `833fc86` (issue #26)

- Candidate: `833fc86f249bb512bf98ff60c53a2bb313cfdb61` on `workflow/issue-26`
- Worktree read: `/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/issue-26`
- Parent compared: `a3406d1`
- Focus: refute the seven trust claims. Findings only with file:line + concrete input/state.

## Conclusion

**PASS** — finding count **0**.

Attempted refutation of all seven claims against the frozen production surface (`scripts/kaola-acp.py`, `scripts/kaola-acp-holder.py`, `scripts/install-local.sh`). None broke.

## Claims

### 1. `list` / `view` / `op_view` never write ACP JSON-RPC to agent stdin

**Not refuted.**

- `command_list` only reads `record.json` and optionally `connect()`s the computed short sock (`probe_socket_ok`); it never calls `socket_request` and never sends a line (`scripts/kaola-acp.py:126-137`, `:148-199`).
- `command_view` sends holder protocol `{"op":"view",...}` on that same short sock (`scripts/kaola-acp.py:206-232`, `:255-263`). That is not ACP JSON-RPC.
- `op_view` snapshots in-memory projection + `pending_permissions`; it does not call `AgentConnection.send_message` / `send_request` (`scripts/kaola-acp-holder.py:1158-1233`). The only stdin writer remains `send_message` (`:277-285`).
- `handle_request` adds `op == "view"` beside existing ops; it does not route view onto `op_prompt` (`:1365-1366`).

**Live state:** mock ACP agent (`watch_projection`) after `start`+`send --no-wait`, then `list` + `view` + `observe`. `MOCK_ACP_LOG` gained **zero** new events (`prompt` / `session_cancel` / `set_config_option` absent). A later `permit` produced `outbound_response` only, which is the existing L0 path.

### 2. L0 permit / prompt / cancel and pending option keys `{id,kind,label}` unchanged

**Not refuted.**

Function-level diff vs `a3406d1`:

| function | result |
|---|---|
| `op_permit` | identical |
| `op_cancel` | identical |
| `on_agent_request` (maps ACP `optionId`/`name` → `{id,kind,label}`) | identical (`:791-798`) |
| `turn_receipt` / `op_state` / `write_record` | identical |
| `op_prompt` | **one added line** after the existing `session/prompt` write: `self.projection.add_user_from_prompt(...)` (`:1059`). Prompt still goes through `agent.send_request("session/prompt", {sessionId, prompt:[{type:text,text}]})` (`:1027-1033`). |

View serializes a **copy** with `optionId`/`name`/`kind` (`:1191-1198`). L0 still exposes the holder-internal dict.

**Concrete state** (live mock, pending request `1001`):

- `observe` / `record.json` options: `{id, kind, label}` (`id=allow_once`).
- `view` options: `{optionId, name, kind}` (`optionId=allow_once`).
- `permit --request-id 1001 --option allow_once` returned `permitted: 1001` (existing JSON-RPC result on agent stdin).

L0 `send --wait` (scenario `normal`) receipt had `thinking_chars` and `schema_version: 3`; it did **not** contain `timeline` / `thinking_text` / `plan` / `messages` / `tools`.

### 3. Unix socket still 0600, parent 0700, Darwin getpeereid / Linux SO_PEERCRED; list/view do not bind TCP/HTTP

**Not refuted.**

`Holder.run` bind/chmod/listen is **unchanged** vs parent (`:1432-1441`): `AF_UNIX`, parent `0o700`, sock `0o600`, `listen(16)`, unlink-if-symlink before bind. `verify_peer` unchanged (`:1405-1421`): Darwin `getpeereid`, else `SO_PEERCRED`.

**Live state** after `kaola-acp grok start` in this review: computed sock mode `0o600`, parent `0o700`, `S_ISSOCK`, not a symlink. `holder.sock` in the record dir is a symlink *to* that short sock.

No `AF_INET` / `HTTPServer` / HTTP / SSE in the candidate diff or in `scripts/kaola-acp.py` / `scripts/kaola-acp-holder.py`. `list`/`view` are CLI + Unix client only.

### 4. `install-local.sh` refuses foreign `$HOME/.local/bin/kaola-acp`; uninstall only owned links

**Not refuted.**

Checks run **before** mutation (`scripts/install-local.sh:143-171`): existing symlink that is not `-ef` the repo scripts → refuse; existing non-symlink → refuse. Install uses a temp symlink + `os.replace` (`:217-224`). Uninstall `unlink`s only after the same `-ef` check (`:232-233`).

**Concrete inputs:**

- Regular file `kaola-acp` containing `foreign-binary\n` (contract test `test_install_refuses_foreign_bin_file`): installer rc ≠ 0, file bytes unchanged.
- Foreign symlink `$HOME/.local/bin/kaola-acp -> /usr/bin/true`: install rc=1, stderr `refusing to replace existing symlink`; uninstall rc=1, stderr `refusing to remove foreign symlink`; target still `-> /usr/bin/true`.

Owned-link install+uninstall is covered by `test_install_local_creates_owned_bin_symlinks` (PASS in this run).

### 5. Prompts still go through existing holder literal path; this issue does not eval prompts

**Not refuted.**

`send` still uses `op_or_holder_lost(..., "prompt", {"text": text, ...})` (`scripts/kaola-acp.py:629-640`). Holder still JSON-RPC-encodes `text` as a prompt block (`kaola-acp-holder.py:1027-1033`). No `eval` / `shell=True` / relay client on the list/view path. `ViewProjection` only stores/concatenates strings (`:425-428`, `:358-365`).

`kaola-tmux.sh` was not in this commit (so it still does not dispatch `list`).

### 6. `list` must not follow `holder.sock` symlink or `record.json` `socket_path`; connect only to computed short sock

**Not refuted.**

`sock_path_for_directory` hashes `str(directory)` under `$TMPDIR/kaola-<uid>-acp/<24-hex>.sock` (`scripts/kaola-acp.py:109-116`). `command_list` probes that path only (`:196`). `command_view` uses `sock_path(args, repo)` from platform/session/repo (`:207`), never `record.get("socket_path")` and never `directory/holder.sock`. `socket_path` appears in `kaola-acp.py` only in a docstring.

**Concrete planted state** (this review):

- `record.json` with live `holder_pid`, `socket_path=/.../foreign.sock`
- `record_dir/holder.sock` → that foreign Unix listener
- no computed short sock

Result: `list` emitted a row with `socket_ok: false`; foreign `accept()` was **not** entered; `view` returned `holder-unreachable` / socket absent; foreign still unconnected.

### 7. No hydra / HTTP / SSE / `session/attach`

**Not refuted.**

Candidate diff grep for `hydra|HTTP|SSE|session/attach|AF_INET|HTTPServer|websocket` hits only a test comment that `#27 follow` is out of scope. Argparse commands gained `view` only (`scripts/kaola-acp.py:565-568`); no `follow` / `attach`. Mock `watch_projection` is stdio JSON-RPC, not a second transport.

## Suspicions (not findings)

- **Install TOCTOU:** check-then-`os.replace` (`install-local.sh:143-155` then `:221-224`) can theoretically replace a foreign file created in the gap. Attacker already needs write to `$HOME/.local/bin` (PATH). Sequential foreign files/symlinks are refused (shown above).
- **Watch contract flake:** `test_l0_send_wait_keys_stay_orchestrator_shaped` and `test_view_matches_sample_key_set_and_types` failed once here because `observe`/`view` ran before in-memory pending landed; `record.json` in that failure already had `{id,kind,label}`. A settled live run (400ms after `watch_projection_emitted`) had both L0 and view pending. Not a key-shape regression.
- **`EventLog.read_since` now walks rotated `.jsonl.1–.3`** (holder `:162-169`). That expands L2 `capture --since` vs parent. Cursor reload was in-scope; capture expansion is not a new agent-stdin or socket-follow hole (files already sat on disk).

## How established

- `git diff a3406d1 833fc86` on CLI/holder/install; function-level identity for L0 permit/cancel/peer/bind.
- Direct reads of frozen `scripts/kaola-acp.py`, `scripts/kaola-acp-holder.py`, `scripts/install-local.sh`.
- Planted `socket_path` + `holder.sock` symlink experiment (claim 6).
- Live mock holder: socket modes, `MOCK_ACP_LOG` around list/view, L0 vs view option keys, permit.
- `python3 tests/contract/test-acp-watch-contract.py -v` (install tests PASS; two pending-timing FAILs as noted).
- Foreign-symlink installer experiment (claim 4).
