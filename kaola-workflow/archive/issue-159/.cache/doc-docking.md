# Doc docking — issue-159 (candidate 2c657580 on workflow/issue-159)

Checked every AGENTS.md documentation surface against the changed public behavior
(kimi-cli dual-root install/uninstall; host-entry matrix root set; #105 scan scope).
Board as of 2026-09-24.

## Changed in this candidate (docked, in scope)

- CHANGELOG.md — one `## Unreleased` entry for the whole change (dual install,
  referrers coverage, #105 scan, matrix/evidence re-measure, contract coverage). DOCKED.
- README.md — `--runtime kimi-cli` usage line now names both roots; the
  reference-counting paragraph records the dual-root receipt sets and uninstall
  semantics. DOCKED.
- docs/host-entry-evidence.md — kimi-cli matrix row lists both user roots; the
  re-measure note carries Issue #119 lineage, the upstream skill-location docs
  (retrieved 2026-09-24), the fleet evidence from the issue's failure, the
  installed 2.0.2 binary fact, and the standing D3 follow-up for the added root.
  DOCKED.
- templates/orchestrator/references/host-entry-matrix.md (+ regenerated
  skills/kaola-project-runner/references/host-entry-matrix.md) — kimi-cli row
  lists both roots and an Issue #159 note; reinstall-every-root and
  dual-withdraw guidance. DOCKED.
- scripts/kaola-acp.py (+ every generated worker skill copy) —
  HOST_SKILL_DISCOVERY_DIRS["kimi-cli"] gains `.kimi-code/skills`, so the #105
  gate scans both roots. DOCKED in api.md's `kaola-acp` surface? — no: api.md
  documents survey/install surfaces, not the discovery-dirs constant; no change
  needed there beyond the runtime table follow-up below.

## No impact (checked, reason recorded)

- docs/architecture.md — describes the installer generically (`install-local.sh`
  delivers those directories to a consuming runtime: a verified named alias ✓);
  its root example is `$HOME/.zcode/skills` (zcode), unaffected. No kimi root
  statement. NO IMPACT.
- docs/conventions.md — no installer or host-entry content. NO IMPACT.
- AGENTS.md — managed project facts carry no kimi-root statement; the release
  pin note is unchanged (content-stage reset is the standing precedent a74119a,
  re-pin is release-side). NO IMPACT.
- docs/codex-host.md, docs/zcode-host.md, docs/grok-bot-host.md — other hosts,
  no kimi content. NO IMPACT.

## Stale surface filed as follow-up (not patched: candidate is frozen)

- docs/api.md — the `--runtime` → destination table (line ~154) still lists
  `kimi-cli` / `dsh` → `$HOME/.agents/skills` only, and the legacy-referrer note
  does not cover the kimi-specific root's kimi-only referrer. Patching it would
  modify the Host-accepted frozen candidate, so it is filed: #161 (P3,
  documentation), body non-empty, OPEN. Same handling as bundle-153 → #155.

## Outcome

DOCKED (one follow-up filed: #161).
