# Documentation docking — issue-123 (candidate 98deeb3)

Checked against AGENTS.md documentation map for changed public behavior (installer install/uninstall semantics, receipt schema field `referrers`, link receipts, bin-link sidecar ledger, uninstall exit code on foreign bin links):

- scripts/install-local.sh usage text — fixed: dropped "the only root Kimi CLI reads / dsh reads"; added reference-count semantics for Skills and bin links (help output verified with `install-local.sh --help`).
- README.md — fixed: kimi-cli line, new shared-block paragraph, bin-link ledger paragraph.
- docs/api.md (installer reference) — fixed: receipt `referrers`, `method: link` receipts, legacy rule, sidecar schema `kaola-project-runner-bin-links/1`, refer/kept outputs, uninstall no longer nonzero on a foreign link.
- docs/architecture.md — fixed: shared-block paragraph.
- docs/grok-bot-host.md — fixed: two bin-link sentences (usable link is referenced; uninstall keeps locator while registration receipt exists).
- templates/orchestrator/references/host-startup.md.tmpl (+ rendered skills/kaola-project-runner/references/host-startup.md) — fixed: `<skills root>` placeholder (issue acceptance 5).
- CHANGELOG.md — Unreleased entry added (kept beside #125's entry after rebase).
- docs/codex-host.md, docs/zcode-host.md, worker Skills, hosts/grok-bot/ — no impact: they defer to the installer reference or do not describe install ownership; render --check PASS confirms generated surfaces are current.

DOCKED
