# Harness ACP compatibility — 2026-09-26 (Pink daily desk, research only)

Session `zcode-kaola-harness-20260926`. Research-only: no live ACP smoke or E2E was run
against any CLI, no orchestrator Host was started, no machine-side harness or runner-skill pin
was changed (Maya owns those after the 03:51 confirm). Every fact below is a read-only network
check (npm registry / `gh api`), a read-only local probe (`--version`, install metadata,
startup logs), or a repository read. Prior desk pattern: `docs/harness-acp-compat-2026-09-24.md`;
the 2026-09-25 desk recorded kimi-cli 2.1.0→2.1.1 (record-only) with no ZCode/ACP motion and no
class 3.

Verdict: **class 3 none; material class 2 = six record-only pin-drift candidates plus one
outstanding record from 2026-09-25.** Nothing here requires action before the next release; all
pin moves are candidates for one #153-style same-commit record batch, and none of them touches
holder, bridge, adapter bytes, or protocol.

## 1. Upstream drift vs platform pins (class 2 candidates, all record-only)

| platform | repo pin | upstream latest | provenance (read-only) | machine today |
|---|---|---|---|---|
| codex | 0.156.1 | **0.157.0** (rust-v0.157.0, 2026-09-25) | GitHub openai/codex releases; npm `@openai/codex` | 0.156.1 |
| claude-code | 2.1.280 | **2.1.282** (npm, 2026-09-25) | npm `@anthropic-ai/claude-code` | 2.1.280 |
| opencode (2.x only) | 2.0.15 | **2.0.16** (`@opencode/cli`, published 2026-09-24T06:32Z) | npm `@opencode/cli` | 2.0.15 |
| kimi-cli | 2.1.0 (repo) | **2.1.1** — unchanged since the 2026-09-25 desk | npm `@moonshot-ai/kimi-code` | 2.0.2 |
| grok | 1.0.40 | **1.0.41** | machine updater `~/.grok/version.json` (checked_at 2026-09-25T06:26Z, 1.0.41 current; no newer found) | 1.0.41 |
| droid | 0.225.1 | **0.227.0** (npm `@factory/cli`; 0.226.0 09-23, 0.226.1/0.226.2 09-24, 0.227.0 09-25) | npm publish times | 0.225.1 |
| dsh | 0.1.5-rc.2 | **0.1.5-rc.3** is npm `latest`; prereleases 0.1.6-alpha.x / 0.1.7-alpha.x / **0.1.7-rc.2** exist beyond it | npm `@deepseek-ai/dsh` | 0.1.5-rc.3 |
| devin | 3000.11.1 | not probed upstream (no safe read-only channel); machine self-updated to **3000.11.3** | `~/.local/share/devin/cli/_versions/` holds 3000.11.1 and 3000.11.3, current = 3000.11.3 | 3000.11.3 |
| cursor-cli | 2026.09.18-9a7762b | no newer version found installed; no upstream channel probed | local versions dir | 2026.09.18-9a7762b |
| zcode | 0.16.9 | **no drift** — see §3 | machine startup logs | 0.16.9 |

Notes per candidate:

- **codex 0.157.0** is a feature release (GPT-6 Sol/Luna models incl. Bedrock, automatic
  background-server startup, conversation fork shortcut, proxy/upload fixes). Nothing in the
  notes touches the ACP transport surface, and `@agentclientprotocol/codex-acp` is unchanged at
  **1.13.1** (no adapter release; npm `latest` still 1.13.1). Same record-only shape as the
  09-24 admission (0.155.1→0.156.1, adapter untouched).
- **opencode**: the desk scope is 2.x only. Confirmed the 2.x channel is the npm package
  `@opencode/cli` (2.0.16 latest, published 2026-09-24). The npm package `opencode-ai`
  (`latest` 1.18.32, 2026-09-21) and the sst/opencode GitHub release line (v1.18.32 newest) are
  the 1.18.x line and are deliberately **not** cited as upgrades.
- **kimi-cli**: 2.1.1 remains latest — no new upstream motion since 2026-09-25. The 09-25
  record (2.1.0→2.1.1) has **not landed** in `platforms/kimi-cli.yaml`: the last platform-file
  edit is `7d8bce7` (#153, 2026-09-24) which set 2.1.0. That record is still outstanding and is
  re-confirmed today; the machine CLI is still 2.0.2 (machine upgrades belong to Maya).
- **grok 1.0.41** self-updated on this machine; `~/.grok/CHANGELOG.json` top entries are a
  `sports_search` tool and a subagent fullscreen fix, both flagged `breaking_change: false`.
- **dsh**: pin rc.2 → stable rc.3 is the record candidate; the forming 0.1.7-rc line is watch
  knowledge, not a candidate.

## 2. Kaola-owned surfaces — no drift

- **Vendored Claude bridge** (`vendor/claude-code-acp`, pin `6c20f28` = upstream
  harukitosa/claude-code-acp commit "Support multiple concurrent sessions via
  ACPX_SESSION_NAME", 2026-03-18): upstream has **zero commits since the pin** (repo dormant).
  No drift. (zed-industries/claude-code-acp — surveyed and then discarded — is a different
  project and is not Kaola's channel; its busy 0.80.0→0.81.2 week is noise for us.)
- **KW checkout** (`/Users/ylmacstudio/Workspace/kaola-workflow`): local HEAD is exactly release
  `kaola-workflow--v12.2.6` (2026-09-24), which is still the upstream latest; **zero upstream
  commits since the release**. KW `install*.sh` scripts carry no npm CLI version pins, so no
  consumer-pin drift exists on the KW side.
- **KPR accepted pin**: `kaola-project-runner-accepted` HEAD == `bba3733` == tag `v0.6.2`
  (intact), and the installed `~/.zcode/skills/kaola-project-runner/SKILL.md` (277 lines) is
  byte-identical to the accepted v0.6.2 render. Machine harness is internally consistent; KPR
  `main` is 27 commits past the pin, all Unreleased (#176/#179 + archives).
- Release-gate awareness only (not drift): the Unreleased #179 change makes `kaola-quota.py`
  restart-required for future releases (reversing #166's quota-only exemption) — remember this
  when the next release's `Seats:` line is written.

## 3. ZCode / ACP surfaces

- **ZCode.app moved 3.14.1 → 3.14.3 (build 7762) on this machine, but the ZCode Protocol
  app-server still reports 0.16.9**: `~/.zcode/cli/log/zcode-2026-09-2{4,5,6}.jsonl` startup
  events all carry `context.version: "0.16.9"`. Platform pin `cli=0.16.9` and wrapper pin
  `80aa4e2` therefore have **no drift** from the app update. (Version read from existing
  startup logs; the GUI main binary was not launched for this.)
- **zcode-acp upstream v0.48.0** (2026-09-25T02:07Z, the only release after v0.47.10): one
  feature commit `6412d0d` (#261) "full dynamic-workflow support with desktop-host-aligned
  remote gate" — adds a workflow-gate/poller/settings-endpoint subsystem (~2.9k source lines +
  tests; new `src/config/workflow-gate.ts`, `src/workflow/poller.ts`, large
  `src/remote/settings-endpoint.ts` additions; session/slash/dispatch handler edits). It does
  **not** touch the compact busy-window (`src/handlers/extensions.ts` absent from the diff) or
  the `usage_update` semantics recorded from 0.47.x. KPR does not consume upstream zcode-acp
  (the Runner drives the native app-server through its own `kaola-zcode-acp.py`; upstream is
  protocol-reference only), so this is watch knowledge, no action.
- **ACP spec repo** (`zed-industries/agent-client-protocol`): 2026-09-25 activity is docs
  registry updates plus `feat(unstable): make MCP-over-ACP request-scoped (#2223)`. Marked
  unstable; Kaola's ten transports are ACP v1 stdio JSON-RPC and do not use MCP-over-ACP.
  All platforms remain `protocol=1`. No action.
- `usage_update` / compaction busy-window: **no new upstream motion** beyond the 0.47.x facts
  already recorded in `docs/harness-acp-compat-2026-09-24.md` §2. The open live-run questions
  there (what the installed backend itself emits during compaction windows) stay open — no
  live smoke was allowed today.

## 4. Machine-vs-pin drift (informational; upgrades are Maya's)

Machine ahead of repo pin: grok 1.0.41 (pin 1.0.40), dsh 0.1.5-rc.3 (pin rc.2), devin 3000.11.3
(pin 3000.11.1) — all self-updated, none breaking. Machine behind record: kimi 2.0.2 vs repo
record 2.1.0 / upstream 2.1.1. claude-code, codex, opencode, droid, cursor-agent, and the ZCode
app-server all sit exactly at their pins.

## 5. Classification summary

- **Class 3 (breaking / must act): none.**
- **Material class 2 (record-only candidates, one batch)**: codex 0.156.1→0.157.0;
  claude-code 2.1.280→2.1.282; opencode 2.0.15→2.0.16 (2.x channel `@opencode/cli`); kimi-cli
  2.1.0→2.1.1 (outstanding from 2026-09-25, re-confirmed); grok 1.0.40→1.0.41; dsh
  0.1.5-rc.2→0.1.5-rc.3. Optional batch platforms when material: droid 0.225.1→0.227.0, devin
  3000.11.1→3000.11.3 (machine-observed).
- **ZCode/ACP notes**: app 3.14.1→3.14.3 with app-server unchanged at 0.16.9 (no pin drift);
  zcode-acp v0.48.0 is a workflow-subsystem feature, irrelevant to the Runner's own adapter;
  ACP spec motion is unstable-only and off the Kaola transport path.
