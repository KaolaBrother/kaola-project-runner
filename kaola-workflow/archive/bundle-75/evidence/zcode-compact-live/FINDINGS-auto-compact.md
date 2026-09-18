# Round-4 live findings: real `trigger:"auto"` compaction + durable-prefix survival on the wire

Date: 2026-09-19 (round 4, authorized bounded validation leg)
Runtime: installed ZCode.app 3.12.3 / CLI 0.16.5, unpatched
Provider: `mock-local/mock-small` — MOCK OpenAI-compatible endpoint
(`http://127.0.0.1:8797/v1`), declared `contextWindow: 8192`. **Not a real
model and not a GLM behavior proof** — the mock supplies transport only; every
compaction step exercised is real ZCode runtime code (threshold check,
`autoCompactIfNeeded`, summary generation, part-record commit, prefix
rebuild).
Isolation: scratch `HOME=/tmp/kpr-i75-mock/home` — provider config
(`$HOME/.zcode/v2/provider_config.json`), session db, credential store, and
user config all resolve under the scratch home via the adapter's own
`ZCODE_PERSONAL_PROVIDER_CONFIG_FILE` env path. **Zero user-global writes**;
no credentials copied/decrypted/logged; `apiKey` is the literal fake
`sk-mock-local-not-a-credential`.
Session: `sess_c46bd933-b8fd-46e9-95d1-c7983a9e4577` (workspace
`/tmp/kpr-i75-native/repo` carrying the planted `AGENTS.md` fixture with
`KPR-AGENTS-DURABLE-5520` + standing instruction `KPR-PREFIX-CARRIER-V1`).

## What was proven live

1. **Real `trigger:"auto"` compaction in installed ZCode 3.12.3.**
   `auto-compact-parts.jsonl`: 23 compaction-related `part` rows —
   `timeline/context_compaction` + `compaction` records with
   `trigger:"auto"`, `auto:true`, `phase:"pre_request"`,
   `compactReason:"context_limit"`, `status:"completed"` — fired whenever the
   session's accumulated tokens crossed the declared 8192 window (observed at
   ~7.5-7.9k request sizes). Seven completed `operationId`s in one session.
   These are the first observed auto-compaction records in this investigation
   (previously only inferred).

2. **The AGENTS.md durable prefix survives auto-compaction — on the wire, in
   the immediately following inference.** `mock-requests.jsonl`: every model
   request after each completed auto-compaction carries the `# agentsMd`
   context section (`has_prefix_marker: true` on 16/17 requests; the single
   `false` entry is the off-band title-generation call, not a conversation
   inference). Post-compact requests (e.g.
   seq=6, seq=18) show `head[2]` = the `<system-reminder>...# agentsMd`
   context section and `tail[0]` = the standing instruction text ("use the
   Read tool on .../SKILL.md and quote the marker it contains") — rebuilt
   per request, outside rewritten history.

3. **Compaction summaries are genuinely applied to history.** Post-compact
   requests carry the runtime-written continuation header ("This session is
   being continued from a previous conversation that ran out of context…")
   in `texts_head[3]` — real summary rewrite, while the `# agentsMd` prefix
   precedes it unchanged.

## What this does NOT prove (stated limits)

- The mock model cannot demonstrate real-model *behavior* (whether GLM-5.3
  would act on the standing instruction post-auto-compact). That leg remains
  proven only for manual `/compact` (round 3, real GLM → read →
  `KPR-SKILL-RELOAD-8842`). Pair the two: prefix delivery is now proven for
  `trigger:"auto"` on the wire; model-visible Skill reload is proven for
  `trigger:"manual"` on a real model.
- Auto-compaction phase observed: `pre_request` (compact before the
  overflowing request). Mid-turn auto-compaction during a single long turn
  was not exercised.
- Declared-window mechanism is a personal-provider model-rule override —
  usable for isolated tests, not a production configuration.

## Isolation & safety record

- Scratch `HOME` only; personal `~/.zcode` untouched (verified `hooks:{}`
  unchanged throughout).
- Mock endpoint `127.0.0.1:8797` localhost-only; fake api key; no real
  credentials anywhere in the fixture.
- Installed app unpatched; no production repo files touched (fixture +
  scratch only).
- Exact stop: `backend.stop()` ran; post-run sweep shows zero residual
  zcode/mock processes.

## Files

- `auto-compact-parts.jsonl` — all 23 compaction part records (sanitized)
- `mock-requests.jsonl` — 17 raw request summaries incl. post-compact prefix
  flags and head/tail excerpts
- `provider_config.json` — the isolated provider declaration (fake key)
- `AGENTS.md.fixture` — the planted standing-carrier workspace file
