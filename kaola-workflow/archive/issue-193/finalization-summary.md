# Finalization Summary — issue-193

## Delivered

Issue #193 (owner authorization comment 2026-09-27): `--runtime droid` now installs into the shared `$HOME/.agents/skills` (with kimi-cli and dsh) through the existing mapping and receipt/referrer mechanism. Droid documents `~/.factory/skills` (Personal) and `~/.agents/skills` (Personal compatibility) as user roots in one bucket where same-name Skills are invalid configuration; the installed droid 0.228.0 binary maps both to one `user-dir` bucket. So the same `--runtime droid` run (install and `--uninstall`) withdraws only the `droid` reference from the retired `$HOME/.factory/skills` under the existing #123 uninstall rules:

- A copy whose last referrer was droid is removed.
- A copy another runtime still refers to is kept, with a duplicate-name warning shown only when both copies exist.
- A droid-only copy with edited bytes, or a same-name directory without a receipt, refuses the whole run before any write.
- Personal Skills and a `kaola-delegator` leftover are never touched.
- A `~/.factory/skills` that canonically resolves to the shared root is skipped.

A pre-ledger receipt counts the runtime(s) mapped to that root when it was written: `kimi-cli,dsh` for the shared root, `droid` for the retired root. No registry, synchronizer, probe, or automatic mass migration was added. Existing installations move only when an operator reruns `--runtime droid`. Nothing was installed on this machine.

Droid-only is the implemented set. Droid's measured discovery set is exactly `{~/.factory/skills, ~/.agents/skills}`, so moving it converges to one copy per name. The other aliases keep their current roots:

- **Codex:** the default destination, with `CODEX_HOME`, user hook, bin links and Delegator ownership tied to it. Docs say duplicates "both can appear". The isolated entry probe on 1.13.1 answered SKILL-NOT-LOADED.
- **Cursor:** also reads `.claude`, `.codex` and `.grok`. Known stale user-root shadow. Precedence undocumented.
- **Devin:** also reads `.claude` and `.cursor`. The `DEVIN_CONFIG_DIR` override would be lost.
- **OpenCode:** also reads `.claude`, and its docs require unique names across locations.
- **Grok:** also reads `.claude` and `.cursor`. Docs are inconsistent about `~/.agents/skills`.
- **ZCode, Claude Code:** retained per the issue.
- **kimi-cli:** the dual-root contract (#159) is unchanged.

Host accepted exact integrated candidate `a94bbad9dac3331e0c021eb52f043152b0514970`. Chain:

- `311a3bf9`: feature.
- `13750619`: review fixes. Duplicate warning only when the retired copy exists; pre-ledger droid attribution only in the retired root; edited-copy doc wording.
- `546fcccb`: late docs-only correction. README 419/477 and `docs/api.md` Kimi sharer wording.
- `f61af092`: late `--help` correction. `install-local.sh` lines 52 and 102 name droid as a sharer.
- `a94bbad9`: non-rewriting merge of main `58363b69` (#192 sink).

## Files Changed

Five paths from main:

- `scripts/install-local.sh`: mapping, `retired_skills_dir`, retired destination role, alias guard, legacy-referrer attribution, `--help`.
- `tests/contract/test-installer-runtimes.sh`: droid loop root and the Issue #193 temp-HOME block.
- `README.md`: two lines.
- `docs/api.md`: installer section.
- `CHANGELOG.md`: Unreleased entry.

## Test Coverage

- `bash tests/contract/test-installer-runtimes.sh` PASS on `a94bbad9`. The block covers:
  - a fresh install;
  - migration of droid-only copies;
  - a co-owned copy kept with a warning;
  - personal Skill and Delegator leftover untouched;
  - an idempotent reinstall;
  - the shared referrer chain droid→dsh→last-referrer removal;
  - uninstall on an un-migrated machine;
  - edited and foreign refusals with no shared write;
  - an aliased root;
  - pre-ledger attribution in both roots;
  - no false warning for an absent retired copy.

  The new assertions fail 24 ways on the pre-#193 installer, and the three 13750619 assertions fail on 311a3bf9.
- `bash tests/contract/test-installer-migration.sh` PASS on `a94bbad9`.
- `./scripts/render-skills.py --check` PASS on `a94bbad9`.
- On `a94bbad9`, `python3 tests/contract/test-issue-148-quota-packages.py` passed, along with the 11 tests that read `docs/api.md` or README (118, 130, 168, 147, 49, 50, 52, 73, 74, 88, 86).
- `./scripts/validate.sh` foreground `rc=0` in 570 s on `13750619`. Installer logic and tests are byte-identical since; later commits changed only help strings and docs. The macOS bash 3.2 watchdog-skip receipts are expected. Log: `/tmp/kpr-193-validate-fg.log`.
- A manual migrate/uninstall scenario under `/bin/bash` 3.2 passed.
- An independent code-reviewer on `311a3bf9` found no correctness defects; its three low notes were fixed in `13750619`.
- Not executed: a live Droid session loading from the shared root, and an install on real user roots (out of scope by instruction).

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- README.md
- docs/api.md
- scripts/install-local.sh
- tests/contract/test-installer-runtimes.sh

## Documentation Docking

DOCKED — see `.cache/doc-docking.md`. The `--help` text, README (two lines), `docs/api.md` and CHANGELOG were updated. The host-entry matrix/evidence and generated Skills had no impact.

## Follow-Up Items

- No follow-up issue filed. The remaining unknowns are those the issue already lists. First, Droid's effective same-name winner across the two roots; the change avoids depending on it by removing droid-only duplicates. Second, same-name precedence for Codex, Cursor, Devin, OpenCode and Grok; those mappings are unchanged.
- Observation (not filed; belongs to the Kaola-Workflow tooling, not this repository): the finalize residue mirror copies every untracked non-`kaola-workflow/` file in the main checkout onto the branch. It did so in #194 and #192, fixed by 3e3404ab and bcbd0bd4. For this finalize, `docs/harness-acp-compat-2026-09-25.md` and `-26.md` were temporarily listed in the main checkout's local, untracked `.git/info/exclude` so the mirror skipped them, and the original exclude file was restored afterwards. The protected files were never moved or edited.

## Status

Ready for sink: all four missions done, Host accepted `a94bbad9`, validation recorded and bound to that tree, docs docked.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-193/.cache/doc-docking.md
- kaola-workflow/archive/issue-193/.cache/final-validation.md
- kaola-workflow/archive/issue-193/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-193/finalization-summary.md
- kaola-workflow/archive/issue-193/mission-ledger.jsonl
- kaola-workflow/archive/issue-193/workflow-state.md
