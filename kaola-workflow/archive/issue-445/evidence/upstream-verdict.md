# Issue #445 upstream ACP verdict (grok CLI 1.0.70 vs Accepted R 1.0.40)

Checked 2026-11-01 before any pin change. Accepted R is
`3d67cf6976381e75ea6a73ee62f88df73c43d5a8`.
`git diff R -- platforms/grok.yaml` is empty: the current manifest matches R,
including `acp_command: grok agent --always-approve stdio`,
`acp_verified_versions: cli=1.0.40;protocol=1`, empty `acp_quirks` and
`acp_wrapper_pin`, `acp_client_capabilities: terminal:false,fs:false`,
`acp_model_config_id: model`, `acp_effort_config_id: reasoning_effort`,
`native_steering: supported`, `acp_steer_method: _x.ai/interject`.
The steering summary cites CLI 1.0.46, not 1.0.40.

## Adapter identity

Grok ACP is the native stdio server inside the CLI. `docs/api.md` records that
there is no separate adapter package for KPR to update. The installed binary
is the published one:

- `command -v grok` → `~/.local/node-v24.14.0-darwin-arm64/bin/grok`
- `grok --version` → `grok 1.0.70 (f50904eaee6c)`
- `npm view @xai-official/grok version` → `1.0.70`
- Installed `bin/grok-native` sha256
  `5c8a688251bf61e35370b828b6a353b0a20fcc3f64000de8a91d426039f29cec`
  equals brotli-decompressed `@xai-official/grok-darwin-arm64@1.0.70`
  `bin/grok.br` (179063008 bytes). No fleet install. PATH was not changed.

Embedded paths in that binary name the linked library
`agent-client-protocol-0.10.4`
(`agent-client-protocol-0.10.4/src/{agent,lib,rpc}.rs`) and the in-tree server
`crates/codegen/xai-acp-lib/src/{channel,gateway,line_reader,normalize,stdin_reader}.rs`
plus `xai-grok-shell/src/session/acp_session_impl/`.

The published crate `agent-client-protocol` 0.10.4 (Zed, repository
`agentclientprotocol/rust-sdk`) depends on `agent-client-protocol-schema`
0.11.4. That schema's `ProtocolVersion::LATEST` is `V1` (`Self(1)`),
`src/version.rs` lines 19-26. It is a protocol constant, not a Grok CLI range.

crates.io reports the newest crate of the same name as 3.6.0 (2026-10-28).
Grok 1.0.70 does not link 3.6.0. 3.6.0 is a library (`bin_names` empty). KPR
cannot swap it in under the native `grok agent stdio` command. The relevant
adapter for this CLI is the server compiled into 1.0.70.

## Declared CLI range

None is declared, and none is invented here.

- `agent-client-protocol` 0.10.4 `Cargo.toml`: no `engines`, no
  `peerDependencies`, no Grok CLI semver.
- `agent-client-protocol-schema` 0.11.4 `Cargo.toml`: same.
- npm `@xai-official/grok` 1.0.40 and 1.0.70 both declare only
  `engines.node >= 20`. Optional dependency pins the matching platform
  package (`@xai-official/grok-darwin-arm64` at the same version).
- The darwin-arm64 package declares `os`/`cpu` only.

1.0.70 is therefore outside any declared CLI range. The version number
`1.0.70 > 1.0.40` is not compatibility evidence. The same crate version string
`0.10.4` appears in the 1.0.40 binary as well (three path hits in each). That
shared number is not compatibility evidence either.

## Surface compared with the unpacked 1.0.40 binary

Unpacked from the registry tarball, not installed:
`grok 1.0.40 (eb1a2256660d)`, native sha256
`3f2aef9618191a2c60d18a5044fa462c9c77bdc4187b02ed716b0394e8d4fef2`.

Both binaries still advertise `grok agent --always-approve` and
`grok agent stdio`. Stdio options remain `--debug`, `--debug-file`, and
`--leader-socket`. 1.0.70 adds a help sentence that a Grok Build unified
leader socket has a daemon beside it. KPR does not pass `--leader-socket`.

Contiguous strings present in both binaries: `session/new`, `session/load`,
`session/prompt`, `session/cancel`, `session/set_config_option`,
`reasoning_effort`, and `x.ai/interject`. The contiguous bytes
`_x.ai/interject` are absent in both. KPR's manifest method is
`_x.ai/interject`, measured on CLI 1.0.46 in the current steering summary.
This string check does not re-measure steer.

## Gate

The linked adapter's declared protocol is 1, and it declares no CLI range.
That authorizes a live KPR probe of the installed 1.0.70 binary
(start, observe, send, read/capture, exact-stop). It does not authorize a
pin change. The pin stays `cli=1.0.40;protocol=1` until those receipts are
GREEN.
