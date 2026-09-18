# Issue #65 — OpenCode: the ACP surface stopped creating sessions (2026-09-18)

> **RESOLVED 2026-09-18, and the cause below was misattributed.** The history is
> kept verbatim; the correction is at the end. It was never OpenCode's install:
> the probing shell exported `HTTP_PROXY`/`HTTPS_PROXY`, OpenCode's session
> bootstrap makes a network call through it, and the failure surfaces as
> `{service: "directory"}`. With the proxy unset, `session/new` succeeds. The
> composite steering path is now proven live on OpenCode.

OpenCode is the one platform whose composite steering could **not** be proven
live in round 3. The blocker is upstream of steering and upstream of the Runner:
`opencode acp` currently refuses to create any session at all on this machine, so
`start` never succeeds and there is no turn to steer. This is recorded with the
reproduction rather than downgraded to "unsupported", because the platform's
steering facts are not what failed.

## The failure

    {"jsonrpc":"2.0","id":2,"error":{"code":-32603,
     "message":"Internal error: OpenCode service failure",
     "data":{"service":"directory"}}}

Through the Runner it surfaces honestly as `start` → `state: error`,
`error.code: acp-session-failed`, carrying OpenCode's own error verbatim
(`live-matrix/opencode-1-start.json`).

## It is not the Runner

Reproduced with **no Runner code in the path** — piping raw JSON-RPC into
`opencode acp`:

| Variation | Result |
|---|---|
| `initialize` | **succeeds**, `agentInfo: {name: OpenCode, version: 1.18.17}` |
| `session/new`, cwd `/tmp/kw-i65-oc/scratch` (fresh `git init`) | `-32603` directory |
| `session/new`, canonical `/private/tmp/...` | `-32603` directory |
| `session/new`, the issue-65 worktree | `-32603` directory |
| `session/new`, the main project root | `-32603` directory |
| `session/new`, `/private/tmp/kw-issue65-probe/scratch-opencode` — **the exact directory that worked at 02:54Z today** | `-32603` directory |
| full `clientCapabilities` (`fs`, `terminal`) instead of `{}` | `-32603` directory |
| empty `OPENCODE_CONFIG` | `-32603` directory |
| pristine `XDG_DATA_HOME` (no cached DB or models) | `-32603` directory |
| `mcpServers` omitted | `-32602` *Invalid params* — so params validation works; the failure above is inside the directory service |

Other exclusions: no other `opencode` process held `opencode.db` after the owned
probe session was stopped (`lsof`), and the non-ACP path of the same binary is
healthy — `opencode run "Reply with exactly: OC-PING"` answered `OC-PING` using
`zhipuai-coding-plan/glm-5.3`, so auth, provider, network and the database are
fine. The failure returns in **0.5 s**, so it is not a network timeout.

## Where it breaks

OpenCode's own log (`~/.local/share/opencode/log/opencode.log`) shows a healthy
ACP start logging `setup connection` → **`global event connected`** → `creating
instance` → `created`. Every failing start today stops at `setup connection` and
never reaches `global event connected`; the next thing emitted is the `-32603`.

Same binary, same version (1.18.17), same machine: ACP session creation worked at
02:28:57Z and 02:54:10Z today (`created id=ses_f4da7867…`, `ses_f4d9070a…`) — the
evidence the round-1 capability row rests on — and has failed on every attempt
since ~03:57Z.

## Consequence and the fix

- The Runner needs no change: it reports the agent's own failure at `start` and
  writes nothing. `steer` was never reached, so nothing about steering is in
  doubt — the composite is platform-independent code, identical to the path
  proven live on the other six non-native platforms.
- The fix belongs to the OpenCode installation: reinstall or upgrade the CLI
  (`brew reinstall opencode`, or a version where `session/new` works) and re-run
  `evidence/probes/live-steer-matrix.sh opencode interrupt`. That is a global
  change to a third-party tool on the owner's machine and was **not** made
  unilaterally under this run's authorization.
- Until then, OpenCode's composite steering is **unverified-live**, not
  unsupported, and this run does not claim otherwise.

## Correction and resolution (2026-09-18, after the owner upgraded the CLI)

The owner installed OpenCode **1.18.31** (a standalone 1.18.17 binary at
`/opt/homebrew/bin/opencode` had been shadowing the Homebrew install; it was
moved aside recoverably to
`/opt/homebrew/var/opencode-backup-MB6kDM/opencode-1.18.17` and `brew link`
succeeded), and their own Runner check started an exact session successfully.

On 1.18.31 the failure still reproduced **for me** — the Runner at the canonical
root, the Runner at the worktree, the baseline (pre-change) Runner from the main
checkout, and the raw JSON-RPC probe, four times running. Since the baseline code
failed identically, the Runner was never implicated either way.

The difference was the environment, not the binary:

    $ env | grep -i proxy
    HTTPS_PROXY=http://123.207.210.89:26927
    HTTP_PROXY=http://123.207.210.89:26927
    $ curl -o /dev/null -w '%{http_code} %{time_total}' --max-time 12 https://models.dev/api.json
    exit 28 (timed out at 12s)

    # same binary, same cwd, proxy removed:
    $ env -u HTTP_PROXY -u HTTPS_PROXY opencode acp   # session/new
    {"sessionId":"ses_f4d200d41ffe5YDpAv2Edjvc9G", ...}

So OpenCode's session bootstrap performs a network fetch, and when that fetch
fails behind this proxy it reports the whole thing as
`-32603 {service: "directory"}`. The earlier conclusion ("the OpenCode
installation is broken; reinstall it") was wrong, and the earlier log reading
that dismissed the `Failed to fetch models.dev cause=TimeoutError` line was the
missed clue. The upgrade to 1.18.31 was not what fixed it.

**Live result** (`live-matrix/opencode-*.json`, 12:57 local, OpenCode 1.18.31,
`acp_session_id: ses_f4d1faf4dffeqyXDck0FxZTSBa`): `start` → `state: ready`;
steer `--steer-mode interrupt` → `interrupted_and_resent`,
`steer_confirmation: cancel-confirmed`, cancelled turn 3 → new turn 4,
`side_effects_possible: true`; the steered turn ended `end_turn` with exactly
`TOPAZ-65-OK`, the codeword planted in the first prompt — same session, context
kept. `stop` clean with `residual_pids []`.

## The defect this episode exposed in the Runner

While `start` was failing, `send` still answered `outcome: in_progress` and the
composite steer answered `steer_consumed: true` with a `new_turn_request_id` —
for a holder whose `acp_session_id` was `null`. The prompt frame was being
written with `"sessionId": null`, the agent rejected it, and only the later
`wait` showed `turn_failed`. A null session must never read as an accepted
dispatch or a successful steer.

Fixed in `kaola-acp-holder.py`: `_no_acp_session()` refuses `op_prompt`,
`op_steer` and `op_steer_interrupt` before anything is written, with
`error.code: no-acp-session`, `outcome: no_session`,
`mutation_status: not_started`, `mutation_performed: false`, and — on the steer
paths — `steer_outcome: not_consumed`, `steer_consumed: false`,
`steer_confirmation: none`, no `new_turn_request_id`. Covered by three contract
tests driven by a new mock scenario `session_new_fails` (the process stays alive
while `session/new` returns OpenCode's exact error shape); all three fail against
the unguarded holder.
