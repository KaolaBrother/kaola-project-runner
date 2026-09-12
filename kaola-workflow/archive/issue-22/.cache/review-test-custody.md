# Test-custody review — Issue #22 / PR #23

Frozen candidate: `69c87a871a5cae74f97d8f3f3967bd820536f0ab` (`cursor/issue-22-permit-oracle-d35d`)
Base: `origin/main`
Focus: whether tests distinguish correct vs incorrect Issue #22 skip-all behavior, whether tests were weakened to pass, and whether production skip knobs lack an oracle.

Ran (read-only) on `.kw/worktrees/issue-22` at the frozen SHA:

- `python3 tests/contract/test-issue-22-bypass-all-approvals.py` → 7 tests OK
- `python3 tests/contract/test-devin-regressions.py` → 30 tests OK
- `python3 tests/contract/test-runner-v2.py` → FAIL (`'cursor-agent acp' not found in 'cursor-agent --yolo acp'`)
- Cached `validate.sh.log` on this SHA: same `test-runner-v2` failure, `VALIDATE_RC=1`
- Simulated the Issue #22 PTY static regex against a copy of `scripts/kaola-tmux.sh` with PTY defaults forced back to `auto`

Kimi ACP `mode=yolo` is the one skip knob with a behavioral oracle (set_config_option event + send `--wait` completing without `permit` / pending permission). Claude/Devin PTY argv have live fake-CLI greps in `test-adapters.sh` / `test-claude-code-runtime.sh` when those scripts run. Focused `./scripts/validate.sh` does not run those PTY scripts or `test-issue-22-bypass-all-approvals.py`.

---

## Findings

### 1. bug — Cursor ACP `--yolo` oracle is inverted

**Where:** `tests/contract/test-runner-v2.py:16` and `:33`

**What is wrong:** `PLATFORMS["cursor-cli"]` still expects substring `"cursor-agent acp"`. Production Issue #22 command is `platforms/cursor-cli.yaml` `acp_command: "cursor-agent --yolo acp"`. Python membership is:

```
"cursor-agent acp" in "cursor-agent --yolo acp"  → False
"cursor-agent acp" in "cursor-agent acp"        → True
```

**Incorrect implementation that still passes this test:** restore pre-22 `acp_command: "cursor-agent acp"` (drop `--yolo`). The assertion succeeds. The candidate's actual skip command fails the test (reproduced on the frozen SHA).

**How established:** ran `python3 tests/contract/test-runner-v2.py` at `69c87a8`; traceback is exactly line 33. `validate.sh` includes this file, so focused validation is red on the correct knob.

No other test requires `--yolo` in `acp_command`. `assertIn(manifest["acp_command"], skill text)` only round-trips whatever YAML already says.

---

### 2. gap — Devin default start is ACP `mode=bypass`, and nothing oracles it

**Where:** production `scripts/kaola-acp.py:37-40` (`ACP_SKIP_MODE["devin"] = "bypass"`) and `scripts/kaola-tmux.sh:137` (`devin) acp_args+=(--mode bypass)`). Tests: `tests/contract/test-issue-22-bypass-all-approvals.py:7-12` explicitly refuse to assert Devin ACP.

**Why it matters:** `platforms/devin.yaml` `default_transport: "acp"`. Public no-flag `start` is ACP, not PTY `--permission-mode dangerous`.

**Incorrect implementation that still passes the suite as written:** delete `"devin": "bypass"` from `ACP_SKIP_MODE` and delete the `devin)` arm at `kaola-tmux.sh:137`. Keep PTY `permission_mode=dangerous` and YAML `launch_summary` mentioning dangerous.

Then:

- Kimi ACP tests still see `mode=yolo`
- `test-adapters.sh` still greps PTY `--permission-mode dangerous` because it forces `--transport pty`
- `test-devin-regressions.py` only checks YAML `launch_summary` + adapter `$permission_mode` passthrough
- `git grep` of `tests/` has no `mode=bypass` / `--mode bypass` / `ACP_SKIP_MODE` assertion

**How established:** grep of `tests/` on the frozen SHA; read `Issue22Kimi*` classes (kimi-cli only); `permission_unless_yolo` in the mock only skips when `configured["mode"] == "yolo"` (`mock-acp-agent.py:315-319`), so it cannot go green/red on Devin `bypass` even if reused.

---

### 3. gap — Claude ACP `mode=bypassPermissions` has no oracle

**Where:** production `scripts/kaola-acp.py:38` and `scripts/kaola-tmux.sh:138`. Tests: `test-issue-22-bypass-all-approvals.py:11-12` say Claude ACP initialize is probe-eof and they will not invent a knob.

**Incorrect implementation that still passes:** remove Claude from `ACP_SKIP_MODE` and remove `claude-code) acp_args+=(--mode bypassPermissions)`. Keep PTY default `permission_mode=bypassPermissions`.

Claude/Devin PTY live tests (`test-adapters.sh:255-260`, `test-claude-code-runtime.sh:118-122`) still pass because they use PTY argv. Claude default transport is PTY, so default start is still skip-all; the untested surface is `--transport acp` / ACP_SKIP_MODE, which this candidate nonetheless ships.

**How established:** same test grep; no test starts `claude-code` ACP against the mock or asserts `ACP_SKIP_MODE["claude-code"]`.

---

### 4. gap — Cursor PTY `--yolo` and OpenCode PTY `--auto` are unasserted; existing argv greps still pass without them

**Where:**

- Production: `scripts/adapters/cursor-cli.sh:46` `ADAPTER_LAUNCH_ARGS+=(--yolo)`; `scripts/adapters/opencode.sh:42` `"$launch_repo" --mini --auto`
- Tests: `tests/contract/test-adapters.sh:263-265`

```bash
grep -Fq "args=$canonical_repo --mini"          # OpenCode
grep -Fq "args=--workspace $canonical_repo"     # Cursor
```

**Incorrect implementation that still passes:** drop `--yolo` from the Cursor adapter and `--auto` from the OpenCode adapter.

Those `grep -F` strings remain substrings of `args=$repo --mini` and `args=--workspace $repo`. Adding the skip flags also still matches. The check cannot distinguish correct from incorrect Issue #22 PTY argv.

Issue #22's own file does not mention Cursor/OpenCode PTY knobs (`test-issue-22-bypass-all-approvals.py:5-12`).

**How established:** read `test-adapters.sh` launch-shape branches vs adapter source; no `--yolo` / `--auto` grep under `tests/`.

---

### 5. gap — Issue #22 tmux-independent PTY oracles match comments / ACP strings, not the PTY assignment

**Where:** `tests/contract/test-issue-22-bypass-all-approvals.py:237-259` (`Issue22PtyDefaultStart`)

The tests strip only the allowlist `case` line (no `DOTALL`), then assert `"bypassPermissions" in remainder` / `"dangerous" in remainder`. After that strip, the candidate runner still contains:

- `claude-code) acp_args+=(--mode bypassPermissions)` (ACP, not PTY)
- comment `Devin PTY dangerous vs ACP bypass` (`scripts/kaola-tmux.sh:87`)

**Incorrect implementation that still passes these two tests:**

```bash
if [[ "$permission_mode_given" != true ]]; then
  case "$platform" in
    claude-code) permission_mode=auto ;;
    devin) permission_mode=auto ;;
  esac
fi
```

leaving ACP `--mode` lines and the Devin comment in place.

**How established:** applied that substitution in memory against `scripts/kaola-tmux.sh` at `69c87a8` and re-ran the same `re.sub` + membership checks. Claude remainder still hit line 138 (`--mode bypassPermissions`). Devin remainder still hit the comment on line 87. Scrubbing that comment without a `permission_mode=dangerous` assignment made the Devin static test fail — proving the comment is a sufficient green.

The class docstring (`:228-230`) claims this is the oracle when nested tmux cannot hold a pane. It does not go RED for missing PTY defaults.

Live `test-adapters.sh` *would* still catch Claude/Devin PTY argv **if it runs**. `./scripts/validate.sh` does not run it.

---

### 6. gap — Devin unit tests were weakened to YAML/passthrough; they no longer lock core default `dangerous`

**Where:** `tests/contract/test-devin-regressions.py:321-347`

Relative to `origin/main`:

- `test_core_default_permission_mode_is_auto` (regex `permission_mode=(\S+)` on the runner) was deleted, not rewritten to the platform-specific skip default
- `assertNotIn("dangerous", adapter_build_launch)` was replaced by `test_dangerous_is_the_skip_all_value_not_dead_code`, whose only assertion is still `'--permission-mode "$permission_mode"'` — the name does not check `dangerous`
- `DevinNoFlagPermissionModeTests` now only parses `platforms/devin.yaml` `launch_summary`

**Incorrect implementation that still passes `test-devin-regressions.py` and focused `validate.sh`:** keep YAML `launch_summary` `--permission-mode dangerous`; leave core `permission_mode=auto` with no Issue #22 case; adapter still forwards `$permission_mode` (so PTY argv stays `auto`).

That is docs-only skip. `validate.sh` runs this file and does not run `test-adapters.sh` / `test-issue-22-bypass-all-approvals.py`.

**How established:** `git diff origin/main...69c87a8 -- tests/contract/test-devin-regressions.py`; ran the file at the frozen SHA (30 OK).

---

### 7. suspicion — mock `parse_known_args` + `permission_unless_yolo` cannot oracle argv skip flags

**Where:** `tests/contract/mock-acp-agent.py:457` (`args, _unknown = parser.parse_known_args()`) and `:315-319` (`configured.get("mode") == "yolo"` only)

Switching off `parse_args()` means leftover agent argv (`--yolo`, `acp`, unknown skip flags) no longer crash the mock and are not recorded as skip configuration. Cursor's production skip is argv `--yolo` on `acp_command`, not `session/set_config_option`. This harness therefore cannot be the Cursor/OpenCode oracle; it also will not fail closed if production starts appending skip flags onto the agent command instead of JSON-RPC mode.

Not admitted as a bug: no current test feeds those extra flags, so there is no demonstrated green-on-wrong Cursor ACP path through this mock — only a missing/unusable oracle (covered in findings 1 and 4).

---

## What is actually locked

| Knob | Production | Distinguishes correct vs incorrect? |
|---|---|---|
| Kimi ACP `mode=yolo` | `kaola-tmux.sh:136`, `ACP_SKIP_MODE` | Yes. `test-issue-22-bypass-all-approvals.py` + `test-acp-contract.py` `Issue22Kimi*` require `set_config_option` mode=yolo and send `--wait` `end_turn` without permit / pending permission. Mock asks permission unless mode is exactly `yolo`. |
| Claude PTY `bypassPermissions` | `kaola-tmux.sh:90` | Yes **when** `test-adapters.sh` / `test-claude-code-runtime.sh` run (fake argv grep + fixture hides approval UI only if those tokens appear). No in focused `validate.sh`. Static Issue #22 tests do not (finding 5). |
| Devin PTY `dangerous` | `kaola-tmux.sh:91` | Same as Claude PTY: live `--transport pty` grep in `test-adapters.sh:269-270` only. Default start is ACP (finding 2). Unit tests weakened (finding 6). |
| Devin ACP `mode=bypass` | `ACP_SKIP_MODE` + tmux `--mode bypass` | No |
| Claude ACP `mode=bypassPermissions` | `ACP_SKIP_MODE` + tmux `--mode bypassPermissions` | No |
| Cursor PTY `--yolo` | `adapters/cursor-cli.sh:46` | No |
| Cursor ACP `--yolo` | `acp_command` | Inverted (finding 1) |
| OpenCode PTY `--auto` | `adapters/opencode.sh:42` | No |
| Grok ACP | none (agent always-approve) | N/A; correctly unasserted |

`test-claude-code-runtime.sh` fixture change (skip approval UI when argv contains `bypassPermissions|dontAsk`, invert `waiting-human` / `native_approval`) is paired with an argv grep. That is a spec update, not a silent weaken, **provided** the grep stays. `activity != 'waiting-human'` alone would be weak; the grep is the real oracle.

---

## Conclusion

Defects. Kimi ACP skip-all is tested as behavior. Claude and Devin PTY skip-all are tested only on the forced-PTY live fake-CLI path, not by the dedicated Issue #22 static oracles and not by `validate.sh`. Devin's actual default start (`mode=bypass` on ACP), Claude ACP `bypassPermissions`, Cursor `--yolo` (PTY and ACP), and OpenCode PTY `--auto` have no positive oracle; Cursor ACP has an inverted one that fails the candidate and would pass dropping `--yolo`.
