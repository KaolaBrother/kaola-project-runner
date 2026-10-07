# KPM architecture-material handoff index (minimal redirect)

Owner directive 2026-10-07: after the KPM bridge verified its target at fixed
commit `a13c6d6f264cf965ca45a07670dbf46cd1eb1e5f`
(github.com/KaolaBrother/kaola-project-manager — `docs/history/kpr/MANIFEST.md`,
`docs/history/kpr/manifest.json`, `docs/history/kpr/reference-check.json`),
KPR retired its duplicate copies of the pure architecture research/design
sources through normal recoverable Git history. This file is the one minimal
redirect index; it authorizes nothing new.

## Path mapping

Every retired KPR path `docs/<rest>` is mirrored byte-identical at
`docs/history/kpr/docs/<rest>` in the KPM repo, pinned at commit
`a13c6d6f264cf965ca45a07670dbf46cd1eb1e5f`:

- retired set: 33 of the 34 authorized candidates — the authoritative list is
  the `retirement_candidates` rows of the bridge verification JSON — plus one
  separately-authorized redirect, `docs/kpm-transfer/kpr-source-inventory.md`
  (superseded by this file; its own set arithmetic omitted
  `docs/research/i272-loop-execution.md`, which the authoritative rows
  include and which was retired). All removed files were sha256-verified
  equal to the mirror at retirement time.
- dependency-retained candidate (1 of 34):
  `docs/designs/ddd-component-2026-10-07/design.md` — in the authorized set,
  retained because the kept `docs/ddd` operating contract cites it nine times
  in-repo; an initial same-day retirement of it was reverted before push.
  Per-file audit: `RETIREMENT-RECEIPT-2026-10-07.md`.
- Pre-retirement KPR copies stay recoverable in KPR Git history (last
  containing commit: `930236f2` lineage; retirement commit: see Git log of
  this file's addition).

## Kept in KPR (not duplicates; operating contracts and live evidence)

- `docs/ddd/` (7 files) — the optional component's operating contract; entry
  links above now point at the KPM mirror.
- `docs/research/i270-tool-entry-audit-complete.md` and
  `docs/research/i270-tool-entry-audit-final.md` — the two A-line defect
  audits.
- `kaola-workflow/archive/**` original workflow evidence (35 entries in the
  bridge manifest) — historical evidence stays in place.
- P2/P3 uncommitted results and `/tmp` originals — preserved in place pending
  KPM classification; never deleted or pushed by this handoff.

## Verification receipts (bridge-owned, read-only for KPR)

- Source manifest (sha256 `b43711a068a3742eca3dcabe33b8b00a63acaefb03887f2bf6c7770c8d2c09cf`,
  source commit `930236f2`):
  `~/Documents/Codex/2026-10-06/task/kpr-architecture-source-manifest.json`
- Target verification (105/105 sha256+bytes pass, 80 Git sources
  byte-identical, `bad: []`):
  `~/Documents/Codex/2026-10-06/task/kpr-target-verification-a13c6d6.json`

Target-material completeness is not KPM design acceptance; no KPR
architecture implementation is revived by this handoff.
