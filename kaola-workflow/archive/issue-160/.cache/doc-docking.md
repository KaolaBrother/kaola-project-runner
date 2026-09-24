# Doc Docking — issue #160

Date: 2026-09-25. Candidate: `3af5dba138355e336528b4422bebeb30535682d1` (workflow/issue-160).

## Checklist against AGENTS.md Documentation Map

| Doc | Affected by this change | Docking |
|---|---|---|
| `README.md` | Yes — installer usage paragraph (`--runtime`/`--platform`/Delegator planning) | Updated in the candidate: owner-preserving refresh wording, fresh-install no_external default, foreign/broken symlink refusal, `--no-orchestrator` skips planning. DOCKED |
| `CHANGELOG.md` | Yes — user-visible installer behavior change | Updated in the candidate (Unreleased, Issue #160 bullet): owner-preserving refresh, referrers stay verbatim, remediation still removes after refresh, foreign/symlink refusals, `--no-orchestrator`, contract coverage list. DOCKED |
| `docs/` | Yes — `docs/zcode-host.md` documents the pin-refresh install flow and ZCode Host root contents | Updated in the candidate (Refreshing the install is part of every pin upgrade, Issue #105 section): owned leftover refresh without ZCode ownership, remediation `--skills-dir ~/.zcode/skills --uninstall` still removes, foreign tree/symlink refusal, `--no-orchestrator` skip. Other `docs/` entries (architecture, conventions, codex-host, grok-bot-host, api) describe surfaces this change does not alter. DOCKED |
| `scripts/install-local.sh` usage/help text | Yes — the help block documents Delegator planning | Updated in the candidate. DOCKED |
| Examples in README | No impact — example commands unchanged; semantics of `--runtime zcode` reinstall clarified in prose. DOCKED |

## Validation of doc claims against implementation

- "Refresh updates content; referrers stay exactly as recorded" — pinned by
  `tests/contract/test-installer-runtimes.sh` (`test_zcode_leftover_refresh_ledger`,
  `test_claude_leftover_refresh_ledger`) and live smoke2 step 3.
- "generic --skills-dir --uninstall still removes after a zcode refresh" — pinned by
  `test_zcode_rmafter_remove` and smoke2 step 5.
- "zcode --uninstall with no prior refresh keeps the copy" — pinned by `test_zcode_unonly_kept`
  and smoke2 step 6.
- "fresh --runtime zcode never creates kaola-delegator" — pinned by `test_runtime_zcode_no_external`
  and smoke2 steps 1/7.
- "foreign tree / foreign or broken symlink refused before any write" — pinned by
  `test_zcode_foreign_delegator_refused`, `test_zcode_foreign_symlink_refused`.
- "--no-orchestrator skips this planning" — pinned by `test_zcode_noorch_untouched`.

## Result

DOCKED — no documentation drift; all changed doc surfaces updated in the candidate and match
implemented behavior.
