# Issue #145 live ACP effort probes (2026-09-23 11:07-11:20 +0800)

Equipment: worktree `scripts/kaola-tmux.sh codex start|stop --repo <canonical root>`, standalone
(inherited KAOLA_ACP_DISPATCHER / KAOLA_ACP_HEARTBEAT_HOST{,_SOCKET} unset so probes do not bind to the
Host heartbeat), KAOLA_ACP_RECORD_ROOT=/tmp/kpr145/records. Surface B via KAOLA_ACP_COMMAND. No
session/prompt was sent (no Codex turns consumed). Every probe stopped; stop receipts residual_pids [].
Local ~/.codex/config.toml carries `model = "gpt-6-sol"`, `model_reasoning_effort = "high"`, so a
`high` read-back alone could be the config default; the `medium` probe discriminates.

| probe | surface | model opt values | effort option under gpt-6-sol | apply | effective read-back |
|---|---|---|---|---|---|
| pinned-start.json | npx @openai/codex@0.153.4 + codex-acp@1.11.0 | gpt-6-sol (post-apply), gpt-6-astra, 5.6-sol/terra/luna, 5.5 | none (ids: mode, collaboration_mode, model) | model applied true; reasoning_effort=high applied false, -32602 Invalid params | gpt-6-sol / effort null |
| 113-start.json | npx @openai/codex@0.155.1 + codex-acp@1.13.0 | gpt-6-astra, gpt-6-sol, gpt-6-luna, 5.6-sol/terra/luna, 5.5 | `reasoning_effort` values low, medium, high, xhigh, max, ultra | model applied true; reasoning_effort=high advertised true, applied true | gpt-6-sol / high (config_id reasoning_effort) |
| 113-medium-start.json | same as 113 | same | same | reasoning_effort=medium applied true | gpt-6-sol / medium (currentValue medium) |
| 113-upgrade-start.json | same as 113, `--tier upgrade` | same | same | gpt-6-astra + reasoning_effort=high applied true | gpt-6-astra / high |

Other facts: 1.13.0 initialize agent_info version 1.13.0, protocol_version 1; bundled @openai/codex 0.155.1
(npx cache). The `_session/steering` extension (SESSION_STEERING_METHOD, `steering:` init meta) is present in
both 1.11.0 and 1.13.0 dist/index.js (static check; live steer needs a turn and was not run).
First 1.13.0 start hit acp-initialize-timeout while npx downloaded the packages (113-stop-1.json, forced
stop); the retry with a warm cache was ready.

Sources: https://raw.githubusercontent.com/agentclientprotocol/codex-acp/main/CHANGELOG.md (1.13.0 2026-09-22,
codex 0.155.0/0.155.1); https://www.npmjs.com/package/@agentclientprotocol/codex-acp (1.13.0 depends
@openai/codex ^0.155.1); https://raw.githubusercontent.com/agentclientprotocol/codex-acp/main/docs/recommended-config-values-extension.md
(effort options model-scoped); https://github.com/agentclientprotocol/codex-acp (README).

## Round 2 — Owner correction issuecomment-5788380284 (target >=0.156.x), 2026-09-23 ~11:45-12:30 +0800

Binary check: `/opt/homebrew/bin/codex --version` → `codex-cli 0.156.0` (symlink to
../lib/node_modules/@openai/codex/bin/codex.js). npm latest: @openai/codex 0.156.1, codex-acp 1.13.0.
Same standalone recipe; surface C = `npx --yes --package @openai/codex@0.155.1 --package
@agentclientprotocol/codex-acp@1.13.0 codex-acp` with `CODEX_PATH=/opt/homebrew/bin/codex` in the caller env.
Process tree proves the child: `node /opt/homebrew/bin/codex app-server` (cp156-process-tree.txt).

| probe | surface | effort option under gpt-6-sol | apply | effective read-back |
|---|---|---|---|---|
| cp156-start.json | C (1.13.0 + CODEX_PATH 0.156.0) | `reasoning_effort`: low, medium, high, xhigh, max, ultra; model values gpt-6-astra, gpt-6-sol, gpt-6-luna, 5.6-sol/terra/luna, 5.5 | model/effort/fast/mode applied true | gpt-6-sol / high |
| cp156m-start.json | C, `--effort medium` | same | applied true | gpt-6-sol / medium |
| cp156u-start.json | C, `--tier upgrade` | — | error `acp-session-timeout` (session/new answered at ~18 s, after the holder's fixed 15 s wait: orphan_response id 2) | — |
| cp156u2/cp156u3-start.json | C, `--tier upgrade` (retries) | same | applied true | gpt-6-astra / high |

Latency A/B (ab-*.json; interleaved, default tier, holder-create → first session_update): bundled 0.155.1
6.1 / 9.7 / 7.8 s; CODEX_PATH 0.156.0 11.2 / 3.4 / 8.2 s; all ready gpt-6-sol/high. Earlier round 1 on
0.155.1 was ~2 s. Latency is time-varying on both surfaces; the cp156u timeout is the holder's 15 s
session/new budget, not a 0.156.0 incompatibility.

npx `@openai/codex@0.156.1` option: npm resolves top-level @openai/codex 0.156.1 but installs a NESTED
`@agentclientprotocol/codex-acp/node_modules/@openai/codex` 0.155.1 (adapter dep `^0.155.1` excludes 0.156),
and the adapter spawns `createRequire(import.meta.url).resolve("@openai/codex/bin/codex.js")` when CODEX_PATH
is unset (dist/index.js startCodexConnection) — so bumping only the npx package pin does NOT move the adapter to
0.156.x. The 0.156.1 darwin-arm64 tarball download stalled through the proxy (killed after ~25 min, partial
~/.npm/_npx dir removed); that surface was not live-probed.

### Round 2 addendum — option-3 surface acquisition retry (Host-bounded, 15 min ceiling), 2026-09-23 ~11:50-12:07 +0800

Command: `npx --yes --package @openai/codex@0.156.1 --package @agentclientprotocol/codex-acp@1.13.0 codex --version`
(run from /tmp/kpr145, wrapped in `perl -e 'alarm 900; exec ...'`). Outcome: **STALLED, not installed.** npm resolved
the tree (placeDep ROOT @openai/codex@0.156.1, darwin-arm64 0.156.1 optional dep) and began extracting
`codex-0.156.1-darwin-arm64.tgz`; the extracted vendor dir stopped growing at ~160 MB (attempt 1 stalled at
~193 MB). The inherited SIGALRM did not end the npm/node process, so the ceiling was enforced manually: killed at
1006 s (SIGTERM, confirmed dead), partial `~/.npm/_npx/154bb1af331cb926` removed (npx cache listing restored to
its pre-attempt state), no residual process. npm debug log: npx156-attempt2-npm-debug.log (no credentials).
The option-3 wrapper surface (`-c 'CODEX_PATH="$(command -v codex)" codex-acp'`) was therefore NOT probed:
no receipts, no adapter/child-version proof, no effort read-back for 0.156.1. Per the Host bound, stopped here.
