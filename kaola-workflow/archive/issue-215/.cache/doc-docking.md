# Doc docking — issue-215

Checked files (changed public behavior: installer gates/reporting, --verify-install
semantics, --bin-links helper report, owner-aware skew refusal route):

- docs/api.md — UPDATED: Installer section gains the pre-mutation render gate,
  post-write requested-payload verification, filtered-scope reporting, and
  obsolete-copy retirement rules; --bin-links paragraph gains the helper report
  and not-upgraded semantics; main-skill-build-skew detail paragraph updated to
  the owner-aware route (Issue #198 extended by #215).
- docs/zcode-host.md — UPDATED: pin-upgrade step 3 rewritten for
  aligned|incomplete|refused receipts, missing/obsolete_owned/unmanaged fields,
  and --expect scoped verification; the main-skill skew paragraph updated to
  the owner-aware route, --verify-install step, and not_started retry.
- CHANGELOG.md — UPDATED: Unreleased entry for #215; Seats: restart not
  required (operator-test paths kaola-acp-holder.py, kaola-zcode-acp.py,
  kaola-quota.py, scripts/adapters, platforms/ all untouched; scripts/kaola-acp.py
  is worker-Skill payload, not in the restart set).
- README.md — no change needed: no flag names, install command shape, or
  documented behavior it pins were altered.
- templates/orchestrator/references/host-startup.md.tmpl — tightened skew
  guidance within the 8192B reference budget (render --check PASS).
- templates/grok-golden/ — untouched (frozen).
- Generated skills/ — regenerated via render-skills.py --write; --check PASS.

DOCKED
