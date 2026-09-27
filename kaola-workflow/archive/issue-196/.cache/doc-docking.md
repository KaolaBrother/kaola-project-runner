# Documentation Docking — Issue #196

Status: DOCKED

Checked against `AGENTS.md`'s documentation checklist and `docs/conventions.md` § Release notes
for release v0.6.6 at Host-accepted content candidate `24b69f6df1296bf29769092c4112376df2c35368`.
This run changes no product behavior; #192-#195 already docked their own surfaces.

| Surface | Decision | Reason |
|---|---|---|
| `CHANGELOG.md` | Updated | `## 0.6.6 — 2026-09-27 (...)` section with `Seats: restart required` and the operator-diff paragraph (`git diff v0.6.5` over holder/bridge/quota/adapters/platforms: `scripts/kaola-quota.py` + ten `platforms/*.yaml`; holder, ZCode bridge, adapters byte-identical); entries for #195, #193, #194 kept, missing #192 entry added; empty `## Unreleased` retained (required by test-issue-162). |
| GitHub release notes | Prepared (not published) | `logs/release-notes-v0.6.6.md` (CHANGELOG section verbatim) and `logs/github-release-body-v0.6.6.md` (concise body requested by Host). |
| `templates/grok-bot/accepted-revision.json`, `hosts/grok-bot/*` | No change | Content stage, bridge `saveable: false` in R; pinning is the later P commit. |
| `README.md`, `docs/api.md`, `docs/architecture.md`, `docs/conventions.md`, `docs/zcode-host.md`, `hosts/grok-bot/INSTALL.md` | No change | Already updated by #192-#195; no version string is declared elsewhere (`git grep 0.6.5` outside CHANGELOG hits only a test comment). |
| `scripts/*`, `platforms/*`, `templates/*`, `skills/*`, `templates/grok-golden/` | No change | Release transaction only; render --check PASS. |
