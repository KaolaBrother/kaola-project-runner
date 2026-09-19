# Issue #98 — live smoke through the generated dsh Skill (mission 5)

Driven by `skills/dsh-kaola-project-runner/scripts/runtime-tmux.sh` at candidate
`cb689a7321f6e84f5d0a3b1e006e9edb9e65b1fc`, in one session this run created and stopped:
`dsh-KT-i98-smoke`, repo `/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner`.
Receipts: `evidence/live/01..08`. No pre-existing session was touched.

| Step | Receipt | Outcome |
|---|---|---|
| preflight | `01-preflight.json` | `protocol_version 1`, `agent_info deepseek-harness-acp/0.0.1`, `auth_methods []`, `login_required false`; capabilities `{cancel, close, list, permission, prompt, resume, set_config_option}` true and `load_session` **false** |
| start | `02-start.json` | `state: ready`, `acp_session_id f69ac426-5ab7-43a8-9846-b14b29f187dd`; `--model opencode-go/deepseek-v4.1-flash` mapped through `acp_model_map` to `["opencode-go","deepseek-v4.1-flash"]` and `applied: true` |
| send | `03-send.json` | `mutation_status completed`, `stop_reason end_turn` |
| capture | `04-capture.json` | `agent_message_chunk` carrying exactly `OPAL-98-OK` |
| send `--no-wait` | `05-send-longturn.json` | `mutation_status in_progress`, `dispatch_event_cursor 3` |
| steer | `06-steer.json` | `interrupted_and_resent`, `steer_confirmation cancel-confirmed`, turn 5 → `cancelled`, new turn 6, `side_effects_possible true` |
| capture `--since 3` | `07-capture-after-steer.json` | the steered turn answered exactly `OPAL-98-STEER`, so the same ACP session kept its context |
| stop | `08-stop.json` | `stopped: true`, **`residual_pids []`**; no `dsh --profile acp` or holder process left, `tmux ls` shows no dsh session |

## What the steer run additionally showed

`side_effects_possible: true` is not boilerplate here. dsh answered the long prompt by putting the
work in a **background job** (`Started it as background job bash-1 (sleep 120; echo LATE)`) and
ending its turn, so cancelling the turn did not by itself cancel the work. The `stop` did: no
`sleep 120` process survived. Interrupting is still not undoing, and the receipt says so.

## Preflight receipt defect found and fixed during this mission

The first preflight reported the `model` option as `"values": [null, null]`. dsh is the first
platform whose select options are **grouped** (one entry per provider, real choices nested inside),
and the holder's probe read `value` off the group entry. An Agent reading that receipt would see
two nameless choices instead of the eight selectable routes. Fixed by
`kaola-acp-holder.py::config_option_values()`, which expands one level of nesting; the re-run
receipt lists all eight `[provider, model]` values and `reasoning_effort`'s `off/low/high/max`.

## Intermittent `install-local.sh` hang seen during the review round — recorded, not explained

Twice during the post-review validation the run wedged: a suite's `install-local.sh` child sat at
~0 s CPU indefinitely (once under `test-installer-migration.sh`, once under
`test-acp-watch-contract.py`). Both times the parent held fd 3 as the write end of the pipe its
child wrote to, with a 16384-byte buffer — the shape of a blocked pipe, not a loop.

What was measured, so the next person does not repeat it:

- `install-local.sh --platform grok` standalone: **exit 0 in 0.2 s**; four concurrent copies under
  one shared `HOME`: **all exit 0 in 0.3 s**. The installer alone does not reproduce it.
- `test-installer-migration.sh` standalone, twice: **exit 0 in 3.3 s and 3.0 s**.
- The unmodified baseline, clean `main` at `d300c7a`: **`BASELINE_EXIT=0`**, 490 lines, zero
  `FAILED`/`RED`/`SKIPPED`.
- This candidate: **exit 0** before the review repairs, then two hangs, then **exit 0** again on a
  quiet machine.

So it is intermittent and did not reproduce on demand. It is **not** claimed fixed, and it is not
claimed pre-existing either — a single baseline pass does not clear a flake. The most plausible
mechanism is a race between the two parallel suite lanes, both of which invoke `install-local.sh`
against one shared sandbox `HOME`; adding a suite to lane A shifts their interleaving. A one-line
`FAILED: VALIDATE_EXIT=143` log with 22 failing suites was also produced during this period — that
was a SIGTERM from stopping a wedged run by hand, not a test result, and it is discarded.

## Suite result

`./scripts/validate.sh` → **`VALIDATE_EXIT=0`** (`evidence/validate-final.txt`, 496 lines):
**zero** `FAILED` / `RED` / `SKIPPED`, 36 unittest blocks all `OK` totalling **680 tests**, 3 bash
acceptance suites PASS, 7 per-suite receipt lines. The two suites this issue added or extended are
in it: `Ran 24 tests` (the new `test-issue-98-dsh-acp.py`) and `Ran 41 tests`
(`test-issue-88-permission-defaults.py`, 35 before the new `DshHasNoApprovalGateAtAll` class).
Zero `SKIPPED` is itself the proof the new suite executed rather than merely being listed —
an inventory entry with no log is reported as `SKIPPED … execution status unknown` and fails the
run, which is exactly how the first attempt caught that the suite was registered in
`python_suites_all` but in neither execution lane. Lanes now partition exactly: 47 = 21 + 26, none
unexecuted, none duplicated.

`./scripts/render-skills.py --check` → PASS, "10 workers + kaola-project-runner + kaola-delegator +
grok-bot host: 1 bridge skill, 2536 B, content stage, unpinned (not saveable); budgets OK".

**One environment caveat, pre-existing and not caused by this change.** With `KAOLA_ZCODE_ENTRY`
and `KAOLA_ZCODE_NODE` exported in the shell — as they are in this session — the existing
`test-zcode-acp-contract.py::test_resolve_runtime_fails_closed` fails, because `resolve_runtime`
falls back to those variables and the test does not clear them. Verified on the **clean `main`
checkout at d300c7a**: it fails there too, and `env -u KAOLA_ZCODE_ENTRY -u KAOLA_ZCODE_NODE` makes
it pass. `validate.sh` does not unset them, so the recorded exit-0 run used `env -u` for those two
variables. This is a pre-existing test/environment coupling, out of scope for Issue #98, and is
reported rather than quietly fixed or hidden.

## `~/.dsh/` integrity

**For this run's own operations: unchanged.** All 16 dsh configuration files hashed byte-identical
before and after every probe and the live smoke — `DSH_CONFIG_UNCHANGED (16/16)`, verified twice.
dsh's own additions under `~/.dsh/sessions/` and `~/.dsh/storages/` are dsh recording its own
session state while being used normally, not an edit by this run.

**A later external change to `~/.dsh/` was then observed, and it is not this run's.** A final check
at the end of the review round found four files differing from the recorded baseline:

| File | mtime | Change |
|---|---|---|
| `.env` | 22:48 | gained `DEEPSEEK_API_KEY` and `ZHIPU_WEB_SEARCH_API_KEY` |
| `settings.yaml` | 22:36 | `agent-default-model` moved from `opencode-go/deepseek-v4.1-flash` to `deepseek-official/deepseek-flash`, `reasoningEffort: high` |
| `profiles/{acp,headless,web}/cordis.patch.yml` | 22:49 | all three gained the same insert: `@deepseek-ai/dsh-mcp-client` mounting a `web-search-prime` streamable-HTTP MCP server at `open.bigmodel.cn` |

Adding provider credentials and mounting an MCP server across three profiles is deliberate
configuration, not a side effect of `dsh --profile acp`, which is the only dsh invocation this run
makes. No command in this run writes a credential, a setting, or a patch layer; the adapter only
`[[ -f ]]`-tests that home, which `test-issue-98-dsh-acp.py::TheAdapterNeverWritesUnderDshHome`
now enforces on the source. Recorded here as an environment change by another party, so the earlier
16/16 line is not read as still true of the machine.

Two consequences worth knowing. The live-smoke receipts above were collected under the *previous*
configuration, so their `["opencode-go","deepseek-v4.1-flash"]` route reflects that state. And with
`DEEPSEEK_API_KEY` now present, the documented credential precondition — a session that starts
`ready` and then fails its first prompt on the pinned `deepseek-official` route — would no longer
reproduce on *this* machine. The precondition itself is unchanged and still correct for a machine
without that key; it simply can no longer be demonstrated here.

The candidate's validation is unaffected either way: `validate.sh` runs the whole suite under a
throwaway `HOME` (`sandbox_home="$(mktemp -d …)"`, `export HOME="$sandbox_home"`), so no dsh
configuration is read or written by it.
