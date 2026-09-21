# #123 — reference-counted shared blocks: a runtime installs or uninstalls alone without touching another runtime's Skills, receipts, or ~/.local/bin links

1. item: Installer: shared Skill receipts carry `referrers` (legacy receipt = runtimes mapping to that root, fail-closed); install of an identical build -> `refer`, a different build -> update that keeps every referrer; uninstall/absent only drop this runtime's reference and delete only when none remain; link method also writes a receipt. ~/.local/bin three links: sidecar `.kaola-project-runner-bin-links.json`, an existing link to a usable (existing, executable) target -> `refer` instead of refusing; dangling still refused; uninstall keeps a link while another referrer or the locator registration receipt exists; the locator registration receipt is never written. #105 scope unchanged.
   status: done
   dispatched: self; output lands on branch workflow/issue-123 in .kw/worktrees/issue-123 (scripts/install-local.sh)
   result: commit e185f11 (install-local.sh refs ledger + test-installer-runtimes.sh updated for ruling-changed behavior: link receipt, bin link kept while codex refers, uninstall keeps a foreign link); installer-runtimes + installer-migration PASS
2. item: Contract tests T-a1..T-c2 (shadow HOME only): order independence, one-sided uninstall with dsh/kimi-cli start/observe/send/capture/stop through the installed Skill, a build difference keeps worker_skill_alignment skew at 0, bin refer vs dangling refusal, bin uninstall protection including the locator; existing installer tests updated where the ruling changes behavior; suite wired into validate.sh
   status: done
   dispatched: self; output lands in .kw/worktrees/issue-123/tests/contract/test-issue-123-shared-refs.py + validate.sh lists
   result: commit 3135ec2 — test-issue-123-shared-refs.py 6/6 tests, 58 checks on the candidate; baseline installer (fe7c806) fails 5/6 (T-b1 pins the unchanged scope and passes on both); wired into validate.sh (all + lane b)
3. item: Docs — install-local.sh usage + README drop "the only root" and state the reference semantics; host-startup.md.tmpl `<skills root>` placeholder; CHANGELOG; render --write
   status: done
   dispatched: self; output lands in .kw/worktrees/issue-123 (scripts/install-local.sh usage, README.md, templates/orchestrator/references/host-startup.md.tmpl, CHANGELOG.md)
   result: commit a1d47ea — usage text, README, docs/api.md, docs/architecture.md, docs/grok-bot-host.md, host-startup template (+ rendered reference), CHANGELOG; render --write/--check PASS
4. item: Gates — render --check and validate.sh rc=0 on the frozen candidate; delivery report with T-a1..T-c2 mapping and doc impact
   status: done
   dispatched: self; validate.sh on a1d47ea, log lands in kaola-workflow/issue-123/evidence/validate.log
   result: kaola-workflow/issue-123/evidence/validate.log — validate rc=0 on a1d47ea (render PASS, installer-runtimes/migration PASS, test-issue-123-shared-refs 6/6 58 checks, sweep residual_pids []); tree clean. Ready for outer acceptance; finalize NOT run (dispatch forbids self-finalize, merge/push before acceptance). Host ACCEPTED a1d47ea; rebased onto 5f4f40c (CHANGELOG Unreleased additive conflict with #125 resolved, both entries kept) → tip 98deeb3; render --check PASS, validate rc=0 (evidence/validate-rebased.log, test-issue-123 6/6 58 checks, residual_pids [])
