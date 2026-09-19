# Issue #94 — run evidence pack

What this directory holds and where each file came from. Nothing here is a
conclusion: the conclusions live in `../mission-list.md`. These are the raw
receipts those results cite, docked into the run so the archive keeps them.

## Contents

| Path | Origin | What it proves |
|---|---|---|
| `NATIVE-SKILL-LIVE-MATRIX.md` | `/tmp/kpr-zcode-native-live-cMR6oa/` (verbatim copy, including addenda 1-3) | The live ZCode 3.12.3 / real GLM ACP matrix, the two binary-source discovery readings, and the explicitly NOT-CLAIMED items |
| `zcode-acp-live/*.json` | same fixture, the receipts the matrix's "Evidence receipts" section names | Real `runtime-tmux.sh` ACP receipts: start, the pre/post `/compact` sends, the captures carrying the `Skill` `tool_call` events, the dollar-form leg, and the exact stop |
| `skill-discovery-wire.md` | distilled from `/tmp/kpr-i94-mock/req-{1,10,11,13,15,17}-head.json` | Which discovery root put `kaola-project-runner` metadata on the wire, per one-prompt probe session |
| `validate/` | this run's three raw validation captures | The passing `validate.sh` run, the first run that failed on an inherited control-plane binding, and the same failure reproduced on unmodified `main` — see `validate/README.md` for the exact commands |

## Why the discovery evidence is distilled, not copied

Each `req-N-head.json` is ~13 KB and is almost entirely ZCode's own system
prompt. `skill-discovery-wire.md` copies the `skills` block lines verbatim and
elides only the skill description, keeping the name and the `file:` path — the
two facts the claim rests on. The full fixture stays at `/tmp/kpr-i94-mock/`
for as long as that scratch directory survives; it is not tracked here.

## Desensitisation

- The live receipts were scanned for credential-shaped strings before copying;
  the only hits were the words "Tokens" (a usage count) and "authorization
  flow" (prose). No key, token, cookie, or account identifier is present.
- Local absolute paths (`/Users/ylminiserver/...`, `/tmp/...`) are kept as the
  run recorded them, matching existing archived evidence in this repository.
- The mock-provider probe ran against a scratch `HOME`; the real user config
  was never read into these files.

## Gaps — evidence this run does NOT have

- **Mission 6 leg (a) receipts.** The `/kaola-project-runner` + trailing-text
  leg on session `zcode-kaola-kpr-i94-entry-a` left no receipt files on disk:
  `/tmp/kpr-i94-entry/` holds only the fixture Git repository, and the ACP
  state directory keeps sockets, not per-session records. The mission result
  stands as the prose record of that leg. The equivalent fact — a native
  `Skill` tool_call for `/kaola-project-runner`, including after `/compact`,
  and the dollar form followed by trailing text — does have raw receipts here,
  from session `zcode-kaola-kpr-native-skill-live-20260919e`.
- **Auto-compaction sessions `sess_689f01f7` / `sess_f5e7468c`.** Their raw
  request dumps are the earlier `/tmp/kpr-i94-mock/req-*.json` generation; only
  the discovery rows above were distilled. The auto-compaction claim itself is
  bounded in the matrix as mock-provider evidence, never model behaviour.
- **Real-GLM automatic compaction.** Never run; the matrix records it as
  NOT CLAIMED and the docs repeat that boundary.
