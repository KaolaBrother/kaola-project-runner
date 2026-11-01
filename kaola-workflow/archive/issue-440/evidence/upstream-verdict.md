# Issue #440 upstream ACP verdict (kimi-code 2.4.1 vs Accepted R 2.2.0)

Checked 2026-11-01 from the canonical checkout before any pin change.
Accepted R is `3d67cf6976381e75ea6a73ee62f88df73c43d5a8`.
`git show R:platforms/kimi-cli.yaml` matches the current manifest:
`acp_command: kimi acp`, `acp_verified_versions: cli=2.2.0;protocol=1`,
`acp_quirks` and `acp_wrapper_pin` empty, `acp_client_capabilities: terminal:false,fs:false`.

## Latest release

`npm view @moonshot-ai/kimi-code version` returned `2.4.1`.
That is the candidate. It is not the Python kimi-cli line.

Published tarballs (registry, not a fleet install):

- 2.4.1 `https://registry.npmjs.org/@moonshot-ai/kimi-code/-/kimi-code-2.4.1.tgz`
  sha256 `e7dac04fa7a155c506d86099584fe442f97a222e44da2c042749968dfcae8e09`
- 2.2.0 sha256 `b7c21c0e4d17b480be9f2c890f14d769244003bf35c80d67f8139d74f5e4d960`

Both packages declare `bin.kimi = dist/main.mjs` and `engines.node >= 22.19.0`.
`@moonshot-ai/acp-server` is a private workspace devDependency at `^0.0.2` in both
package.json files. It is not on the public npm registry. The running adapter is the
copy bundled into `dist/main.mjs`.

## Adapter identity and declared CLI range

Tagged source `packages/acp-server/package.json` is byte-identical at
`@moonshot-ai/kimi-code@2.2.0` and `@moonshot-ai/kimi-code@2.4.1`:

- name `@moonshot-ai/acp-server`, version `0.0.2`, `private: true`
- dependency `@agentclientprotocol/sdk: ^1.3.0`
- no `engines`, no `peerDependencies`, no CLI semver range

`packages/acp-server/src/version.ts` is also byte-identical:

- `protocolVersion: 1`
- `specTag: v0.10.x`
- `sdkVersion: 0.23.0` (the adapter's own spec tuple, not a Kimi CLI range)
- `MIN_PROTOCOL_VERSION = 1`

No CLI range is declared. None is invented here. The pair under test is the
published CLI tarball that bundles this adapter. The adapter package version
string `0.0.2` did not change between 2.2.0 and 2.4.1, so that number is not
evidence of compatibility.

## Session error mapping (the concrete seam)

`packages/acp-server/src/session.ts` at 2.4.1 adds 17 lines to `mapPromptLaunchError`.
The published 2.4.1 `dist/main.mjs` contains the same function. The 2.2.0 bundle
contains `turn.agent_busy` and does not contain `session.occupied` or `session.stale`.

`RequestError.invalidRequest(data, additionalMessage)` in that bundle is:

- JSON-RPC code `-32600`
- message `Invalid request: <additionalMessage>`
- `data` is the first argument

2.4.1 mapping:

- `turn.agent_busy` → `-32600`, `data.code = turn.agent_busy`, engine message passed through
  (local `assertNoActiveTurn` still uses `another turn is already in progress`)
- `session.occupied` → `-32600`, `data.code = session.occupied`, engine message passed through
- `session.stale` → `-32600`, `data.code = session.stale`, message replaced with
  `Session was updated by another client. Close and reopen the session, then retry.`
  The engine text names the internal session id and does not cross ACP.

Engine facts at the same tag (`sessionRunGateService.ts`, `node-fs/sessionLockService.ts`):

- A run holds a pid lock. `KIMI_CODE_SESSION_LOCK=0` disables it. A dead holder can be reclaimed.
  `evict()` is an explicit takeover and logs `taking over session lock`.
- Occupied is thrown when another live pid holds the lock. The node SDK's `takeOverLock()`
  calls that evict path. The ACP mapper does not.
- Stale is thrown when this process's wire was `externallyModified` before `begin()`.
  The gate releases the lock and rejects. It does not reload inside ACP.
- The lock schedules release 3000 ms after the session goes idle.

The ACP server does not retry, does not call `evict`, and does not read `KIMI_CODE_SESSION_LOCK`.
KPR must not add those behaviors. Occupied and stale stay distinct from `turn.agent_busy`
by `error.data.code`. A numeric `-32600` alone is not the identity.

## Other tagged diffs that do not expand the holder

- `packages/acp-server/test/lifecycle.test.ts`: workspace lease `acquire`/`dispose`
  instead of `getOrCreate`. No occupied/stale assertion.
- `packages/acp-server/src/acp-terminal/acpTerminalRunner.ts`: drops an explicit
  `terminal = undefined` on a host object and uses `toReversed()`. KPR still
  advertises `terminal:false`. That is not a reason to offer a terminal capability.
- Changelog entries for occupancy prompts, crash-lock recovery, queued `/compact`,
  and permission dialogs describe TUI/Web/node-SDK behavior. The ACP path that
  reaches KPR is the `mapPromptLaunchError` seam above. Compact and permission
  behavior is not adopted from those notes.

## KPR baseline before the live probe

Current holder stores the raw JSON-RPC error on the turn receipt, then
`summary_from_acp` keeps the numeric `code` and `message` and drops `data`.
A `-32600` summary therefore collapses occupied, stale, and busy unless the
caller reads `data.code` or the message. The holder does not auto-replay a
failed prompt and does not take over a foreign lock. One holder refuses a
second prompt locally as `prompt-in-progress` before a second `session/prompt`.

## Gate

Source and the published 2.4.1 bundle establish a real ACP seam on an undeclared
CLI range, with protocol negotiation still at 1. That authorizes a sandboxed
2.4.1 probe. It does not by itself authorize a pin update. Pin, quirks, and any
summary change wait on start / observe / send / capture / exact-stop plus
occupied and stale receipts that keep foreign ownership.
