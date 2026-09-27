# Harness ACP compatibility — 2026-09-25 (desk digest, uncommitted)

Daily desk research, session `zcode-kaola-harness-20260925`. Read-only: no live smoke/E2E/UAT,
no pin or CLI upgrades, no issues opened or people pinged, no Host started or attached, nothing
committed. Machine probes are `--version` prints and file reads only. Pickup target: Pink ~03:51.

## 0. Verdict for pickup

- **Class 3 (must/breaking): none.** No upstream moved a pinned ACP surface today.
- **Material class 2 (soft-forward worth admitting): one, record-correctness only —
  kimi-cli record 2.1.0 → 2.1.1.** Moonshot shipped `@moonshot-ai/kimi-code@2.1.1`
  (2026-09-24T07:24Z) whose sole patch theme is "roll back some of the overly defensive changes
  in 2.1.0". Yesterday's 2.1.0 record is un-probed and now names a version upstream itself
  partially reverted; the record should move to 2.1.1 whenever the next record batch lands.
  No wire/protocol claim changes with it (`kimi acp` surface untouched by the note text).
- **Optional batch (record-only `acp_verified_versions`)**: grok 1.0.41, devin 3000.11.3,
  dsh 0.1.5-rc.3, claude-code 2.1.281, droid 0.226.2 (or conservative 0.225.2),
  opencode 2.0.16 (2.x channel only), plus the kimi 2.1.1 item above.
- **ZCode/ACP: no motion.** zcode-acp still v0.47.10; ZCode App 3.14.3 / CLI 0.16.9 constant
  (#154 closed verdict A yesterday); ACP protocol v1 wire unchanged (v1.9.x additions are
  unstable-channel only).

## 1. Consumer state (both repos, re-verified today)

- **KPR** `main` = `d9c018c`, clean, 0 behind `origin/main`. Latest tag `v0.6.1` (tag object
  `cac0d13`, content R `c1dc92e` per the accepted pin). Seven commits after the content commit:
  the grok-bot pin accept `a4b6801`, then #159 (kimi-cli dual-root install), #160 (delegator
  refresh), #161 (docs). None touch platform pins — all ten `platforms/*.yaml` match the #153
  state read today. No tag since v0.6.1, so the next release starts a fresh grok-bot pin cycle.
- **KW** `main` = `1cbd7e2a` = tag `kaola-workflow--v12.2.6`, clean, 0 behind origin. No newer
  tag. KW's only CLI version references are Grok floor facts (`templates/agents/runtime-capabilities.json`
  `version_floor: 1.0.40` for the grok-4.7 catalog claim, `docs/decisions/0019`, `docs/grok-edition.md`);
  a 1.0.41 patch does not break a floor. No other CLI pins exist in the KW tree.
- **KPR issue tracker**: nothing open; #153 and #154 both closed 2026-09-24 (#154 verdict A:
  no pin/adapter change; live-verified App 3.14.3 → CLI 0.16.9, adapter `kaola-zcode-acp` 0.3.3,
  reference pin `80aa4e2`).

## 2. Records vs machine vs upstream (probed 2026-09-25, read-only)

| platform | record (`acp_verified_versions`) | machine (`--version`) | upstream latest | drift |
|---|---|---|---|---|
| codex | cli=0.156.1; adapter=1.13.1 | 0.156.1 | 0.156.1 stable (0.158.0-alpha.9 is pre-release) | none |
| claude-code | cli=2.1.280; bridge=6c20f28 | 2.1.280 | npm 2.1.281 | optional |
| cursor-cli | cli=2026.09.18-9a7762b | 2026.09.18-9a7762b | no public per-version feed found | none known |
| droid | cli=0.225.1 | 0.225.1 | npm @factory/cli 0.226.2 (0.225.2 exists) | optional |
| dsh | cli=0.1.5-rc.2 | 0.1.5-rc.3 | npm @deepseek-ai/dsh latest 0.1.5-rc.3 (next 0.1.7-rc.2) | optional; machine ahead of record |
| grok | cli=1.0.40 | 1.0.41 | 1.0.41 current (Homebrew `grok-build` formula; ACP registry) | optional; machine ahead of record |
| kimi-cli | cli=2.1.0 (record-only) | 2.0.2 | @moonshot-ai/kimi-code 2.1.1 (2026-09-24T07:24Z) | **material class 2**; machine 2 minors behind |
| opencode | cli=2.0.15 | 2.0.15 | @opencode/cli 2.0.16 (2.x channel; tag v2.0.16, no release body) | optional |
| devin | cli=3000.11.1 | 3000.11.3 | no public feed; local cache holds 3000.11.1 + 3000.11.3 | optional; machine ahead of record |
| zcode | cli=0.16.9; adapter=kaola-zcode-acp | App 3.14.3 (CFBundleVersion 3.14.3.7762); CLI 0.16.9 per #154 | zcode-acp v0.47.10 unchanged | none |

Machine-side freshness debt (Maya's call, after Pink's confirm): kimi 2.0.2 (record 2.1.0/2.1.1),
droid 0.225.1 (< 0.225.2/0.226.2), opencode 2.0.15 (< 2.0.16), claude 2.1.280 (< 2.1.281).
Grok, devin, dsh on this machine already run ahead of the records.

## 3. Upstream evidence per surface (what was checked, 2026-09-25)

- **Codex**: `openai/codex` latest stable release is `rust-v0.156.1` (2026-09-23T02:41Z) = the
  pin; beyond it only the `rust-v0.158.0-alpha.N` series (alpha.9, 2026-09-24T17:49Z; no 0.157
  stable appeared). npm `@openai/codex` latest = 0.156.1; npm `@agentclientprotocol/codex-acp`
  latest = 1.13.1 = pin. Watch: when 0.158 goes stable, re-verify the paired CLI+adapter bump
  pattern from #153.
- **zcode-acp**: `william0wang/zcode-acp` latest release still `v0.47.10` (2026-09-23T13:51Z);
  no 0.47.11+ and no 0.48.x as of today. npm names remain unrelated/absent (matches "never npm").
- **ZCode app**: `/Applications/ZCode.app` CFBundleShortVersionString 3.14.3 (CFBundleVersion
  3.14.3.7762) — unchanged from #154's live check yesterday; CLI 0.16.9 constant across
  3.14.1→3.14.3 per #154. Update feed `https://cdn-zcode.z.ai/zcode/electron/releases/latest-mac.yml`
  still answers 404 from this network (re-tried today) — channel manifest stays unverified,
  as #154 recorded.
- **kimi-cli**: `moonshotai/kimi-code` latest release `@moonshot-ai/kimi-code@2.1.1`
  (2026-09-24T07:24Z): patch "Roll back some of the overly defensive changes in 2.1.0".
  2.1.0 (2026-09-23) is a minor with TUI-facing changes; nothing ACP-named in either body.
  The old `kimi-cli` repo is archived in favor of kimi-code.
- **opencode**: 2.x lives on npm `@opencode/cli` (machine's install channel), latest **2.0.16**;
  the registry's `opencode-ai` `latest` dist-tag still serves the 1.18 line (1.18.32) — per
  standing rule, 1.18.x is never a recommendation or citation source. Repo
  `anomalyco/opencode` has tag `v2.0.16` but publishes no GitHub Release body for the 2.x line,
  so 2.0.16's contents are unreviewed here; the bump stays record-only/un-probed.
- **claude-code**: npm `@anthropic-ai/claude-code` latest 2.1.281. CHANGELOG highlights are
  Gateway/Bedrock/MCP/plugin/UX fixes plus resume/retry crash fixes; nothing naming the
  stream-json input channel, `--resume`, or ACP-adjacent behavior the vendored bridge depends
  on. Optional at most.
- **droid**: npm `@factory/cli` latest 0.226.2 (0.225.2, 0.226.0, 0.226.1 in between). No
  public release-notes feed reachable (GitHub `Factory-AI/factory` exposes no releases;
  factory.com/changelog 404 from this network), so ACP-relevance of 0.226.x is unverified —
  the native-ACP surface (`droid exec --output-format acp`) is only record-pinned at 0.225.1.
- **grok**: upstream is `xai-org/grok-build`; 1.0.41 is current (Homebrew formula
  `grok-build`, ACP registry listing) and this machine already runs 1.0.41 vs record 1.0.40.
  Itemized 1.0.41 notes not retrievable (repo carries no CHANGELOG.md at main and no releases
  body). KW's grok-4.7 catalog facts cite 1.0.40 as a floor — unaffected by a patch.
- **dsh**: npm `@deepseek-ai/dsh` dist-tags: `latest 0.1.5-rc.3` (machine matches), `next
  0.1.7-rc.2`, `alpha 0.1.7-alpha.2` — the 0.1.7 line is moving; when `latest` crosses to
  0.1.6/0.1.7 the dsh quirks (launcher version, ACP profile behavior) deserve a re-read.
- **devin / cursor-cli**: self-managed version caches; devin machine 3000.11.3 (record
  3000.11.1); cursor-agent machine = record 2026.09.18-9a7762b, no public per-version feed
  (cursor.com changelog is app-level, Sep 23 entries are bots, not CLI ACP surface).
- **ACP protocol**: `agent-client-protocol` v1.9.0/v1.9.1 + `schema-v1.23.0` (2026-09-18):
  additions are unstable-channel only — *(unstable)* v1 session notice capability (#2171),
  *(unstable-v2)* message ID on prompt insertion (#2175); v1.9.1 is a Rust-side null-payload
  fix. TS SDK `@agentclientprotocol/sdk` 1.5.0 (2026-09-21) tracks the same schema. No v1
  wire change; the Runner's hand-rolled zcode adapter and vendored claude bridge are
  unaffected. Revisit only if a session-notice-style capability is promoted to stable.

## 4. Watch list for the next desk

1. Codex `0.158.0` stabilization (9 alphas and counting) → paired codex-acp re-check (#153 pattern).
2. dsh `latest` crossing to 0.1.6/0.1.7 (next/alpha channels already there) → quirks re-read.
3. zcode-acp anything after v0.47.10; ZCode app feed manifest still unfetchable (404).
4. #154 standing live-probe items unchanged: real compact-window trigger; permission-mode
   (interaction/requestPermission) probe.
5. ACP protocol unstable capabilities (session notice, v2 prompt-insertion ID) reaching stable.
6. kimi machine binary still 2.0.2 while the record moves to 2.1.x — Maya's freshness call.

## 5. Evidence trail

Local: `git log/tag/status` + `git fetch` (0 behind) both repos; `platforms/*.yaml` read;
`gh issue view 153/154`; `--version` probes for nine CLIs; symlink/channel reads
(`~/.grok/downloads`, `~/.local/share/devin|cursor-agent`, `@deepseek-ai/dsh`, `@opencode/cli`,
`~/.kimi-code`); ZCode `Info.plist` via `defaults read`; `https://cdn-zcode.z.ai/.../latest-mac.yml` 404.
Network (read-only): `gh api` on `openai/codex`, `william0wang/zcode-acp`,
`zed-industries/agent-client-protocol`, `moonshotai/kimi-code`, `anomalyco/opencode` (tags),
`xai-org/grok-build`, `Factory-AI/factory` (no releases exposed); `npm view` on
`@agentclientprotocol/codex-acp`, `@anthropic-ai/claude-code`, `@opencode/cli`, `opencode-ai`
(dist-tags only, 1.x line deliberately uncited), `@factory/cli`, `@deepseek-ai/dsh`,
`@openai/codex`, `@agentclientprotocol/sdk`; anthropics/claude-code CHANGELOG (2.1.280/2.1.281).

Not verified today (unchanged from yesterday): any live ACP run; zcode backend behavior in a
real compact window; 0.226.x droid ACP behavior; 2.0.16 opencode ACP behavior; 2.1.1 kimi ACP
behavior. All record bumps named above stay record-only until a live run says otherwise.
