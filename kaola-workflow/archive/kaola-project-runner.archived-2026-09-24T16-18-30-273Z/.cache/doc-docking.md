# Doc docking evidence — Issue #161

Candidate: `4d22ffde235a2b594c06489f9197ce212b1f1e51` (rebased onto `d7f4f76`)
Change: `docs/api.md` only (+9/−2) — docs-only correction of the `--runtime kimi-cli`
destination table and the reference-counting paragraph after #159 shipped dual-root.

## Verdict

DOCKED

## Checked files

| Surface | Status | Reason |
|---|---|---|
| `docs/api.md` | fixed | The only remaining stale surface. Destination table listed `kimi-cli` / `dsh` → `$HOME/.agents/skills` only; now splits `dsh` (single root) from `kimi-cli` (BOTH roots, own receipt set). Referrers paragraph keeps the legacy-referrer example and adds the Kimi-specific pre-ledger = `kimi-cli`-only rule plus dual-root uninstall semantics. |
| `README.md` | no impact | Already updated by #159 (`install-local.sh --runtime kimi-cli # ~/.agents/skills AND ${KIMI_CODE_HOME:-~/.kimi-code}/skills`, and the reference-counting paragraph naming both roots and the kimi-cli uninstall behavior). Verified by reading lines 410 and 466–475; no stale claim remains. |
| `CHANGELOG.md` | no impact | #159's Unreleased entry already documents the dual-root install, per-root receipt sets, and the uninstall/referrer semantics. Docking convention in this repo is that a pure `docs/api.md` correction ships without its own CHANGELOG entry (precedent: `9eb28d0`, #155, which touched only `docs/api.md`); a second entry would duplicate #159. |
| `docs/host-entry-evidence.md` | no impact | Already updated by #159 to list both kimi-cli roots with the re-measure note. |
| `docs/zcode-host.md` | no impact | ZCode-only surface; unrelated to kimi-cli destinations. |
| `skills/…/references/host-entry-matrix.md` | no impact | Generated surface; #159 already carries both roots. Not hand-edited (generated output). |
| `scripts/install-local.sh` `--help` | no impact | Shipped usage text already states both roots and the dual-root uninstall; the docs now match it. |

## Verification basis

Wording was transcribed from shipped behavior, not invented:

- `scripts/install-local.sh` @ `2c65758`: `dest_parents=(...)` dual map gated on
  `base_runtime == kimi-cli`; `kimi_extra_skills_dir()` → `${KIMI_CODE_HOME:-$HOME/.kimi-code}/skills`;
  `legacy_referrers` resolved per destination, falling back to `self_ref`.
- Live throwaway-`HOME` install: both roots populated; `dsh` install made shared referrers
  `['dsh','kimi-cli']`; `kimi-cli --uninstall` left the shared root `kept: … (still referenced by dsh)`
  and removed the Kimi-specific root; a referrer-stripped (pre-ledger) Kimi-specific receipt was
  still removed by kimi-cli uninstall, confirming it counts as kimi-cli alone.
- Claude Code review seat: VERDICT PASS on `59fe96a2` (same bytes; rebase left the `docs/api.md`
  blob sha `0fce6bb9…` and sha256 `6583c74e…` identical).
