# Issue #413 stage 1 — catalog fact evidence (2026-10-27, MacBook, read-only probes)

No ACP seat was started. No /model picker. No install/upgrade.

## Droid: DeepSeek V4.1 Flash 1017

- Installed `droid --version` = `0.241.1` (`@factory/cli` under node-v24.14.0).
- `droid exec --help` (0.241.1) catalog lists `deepseek-v4.1-flash — DeepSeek V4.1 Flash`
  (efforts `[off, low, high, max]`, default high); no `1017` anywhere.
- `droid exec --model deepseek-v4.1-flash --reasoning-effort max --list-tools` → accepted
  ("Available tools for DeepSeek V4.1 Flash").
- `droid exec --model deepseek-v4.1-flash-1017 --reasoning-effort max --list-tools` →
  `Invalid model: deepseek-v4.1-flash-1017` (exit 1) on 0.241.1.
- 0.241.1 embedded registry: `deepseek-v4.1-flash` = fireworks `deepseek-v4p1-flash`,
  baseten `DeepSeek-V4.1-Flash`, `billingPool:"core"`, `tier:"standard"`; zero `1017` strings.
- `~/.factory/cache/feature-flags.json` (2026-10-26 16:47): `provider_routing.models` contains
  BOTH `deepseek-v4.1-flash-1017` and `deepseek-v4.1-flash` (distinct keys); no
  `deepseek_v4_1_flash_1017` flag entry (0.241.1 does not know that flag).
- npm `@factory/cli` latest = `0.249.0` (published 2026-10-24T02:02Z). Downloaded tarball only
  (`npm pack @factory/cli-darwin-arm64@0.249.0` into `/tmp/kpr413-droid249`, sha256
  `cde7eedb3fd52e8690814bdc28c45e5eade9c837ff7cf0f8ef3a45d7704c3b09`), not installed. Its
  embedded registry declares:
  `"deepseek-v4.1-flash-1017":{id:"deepseek-v4.1-flash-1017",name:"DeepSeek V4.1 Flash 1017",
  featureFlag:DeepSeekV41Flash1017, apiProviders:[fireworks,baseten,databricks],
  fireworks modelId accounts/fireworks/models/deepseek-v4p1-flash-1017,
  reasoningEffort:{supported:["off","low","high","max"],default:"high"}, tier:"standard",
  billingPool:"core", newUntil 2026-10-22}`; feature flag
  `DeepSeekV41Flash1017:{displayName:"DeepSeek V4.1 Flash 1017 (Droid Core)",
  statsigName:"deepseek_v4_1_flash_1017",defaultValue:false}`. `deepseek-v4.1-flash` remains a
  separate entry (non-1017 provider model ids).

Conclusion: the native 1017 identity is `deepseek-v4.1-flash-1017` (NOT `deepseek-v4.1-flash`,
which is a separate catalog entry with different provider model ids); billingPool `core`; `max` supported. Runtime caveat for the
later live stage: the installed 0.241.1 rejects the id, so live use needs a Droid CLI that ships it
(present in 0.249.0) and the account-side `deepseek_v4_1_flash_1017` feature flag, whose state is
unknown. Elite class kept: Factory's `tier:"standard"` is its pricing tier (kimi-k3 had the same)
and does not contradict KPR's Elite class.

## Cursor: xhigh through ACP configOptions

- `cursor-agent --version` = `2026.10.22-27dcf5f`; `--list-models` advertises `grok-4.7-xhigh`,
  `grok-4.7-xhigh-fast`, `claude-opus-5-5-xhigh`, `claude-opus-5-5-xhigh-fast`; no model or tier
  named "open".
- Existing holder records (`/tmp/kaola-501/cursor-cli/*/*/record.json`, 14 sessions with the
  parameterized picker): model `grok-4.7` advertises `reasoning_effort` options
  `[low, medium, high, xhigh]`; one session (`cursor-KPM-i762-l9c3`) shows currentValue `xhigh`.
  Start evidence there applied model `grok-4.7` via map from `grok-4.7-high`, effort through
  config id `reasoning_effort` resolved from candidates `reasoning_effort;effort`.
- No recorded ACP session with model `claude-opus-5-5`: the Opus `effort` option's value list
  (whether it advertises `xhigh`) is NOT observed; native catalog lists `claude-opus-5-5-xhigh`.
  Opus xhigh application over ACP stays unverified until the authorized live stage.

## "Open" tiers

Unresolved. No `open` model, tier or preset in Cursor's native catalog, KPR manifests or ACP
records. Remains an open question in #413; nothing removed.
