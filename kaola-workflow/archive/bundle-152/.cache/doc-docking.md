# Documentation Docking — bundle-152 (Issue #152)

DOCKED

Candidate: workflow/bundle-152 @ ed07232 (validated_candidate_hash 37358be816d8e908f3084f59ffbd45caff4057da11453ff5c649d5c362bf38b4)

## Checked files

| File | Action / reason |
| --- | --- |
| `scripts/install-local.sh` | Fixed in-place: `--help` text now says "all ten worker Skills" (the user-facing API surface of the installer). |
| `docs/codex-host.md` | Fixed in-place: "the ten `<platform>-kaola-project-runner` workers" (line 17). |
| `docs/zcode-host.md` | Fixed in-place twice: "one of the ten worker target CLIs" (line 11) and "the ten `<platform>-kaola-project-runner` workers" (line 16). |
| `scripts/kaola-grok-bot-verify.py` | Fixed in-place: module docstring says "the ten platform workers" (user-facing prose discovered by the gate; Host-accepted). |
| `README.md` | No impact: no "nine" platform-count wording present (repo-wide grep of README.md: zero hits). |
| `docs/` (other pages), `docs/` (architecture) | No impact: repo-wide grep for `nine platform/all nine/the nine/one of the nine` in docs/ returned only codex-host.md and zcode-host.md, both fixed. |
| `CHANGELOG.md` | No impact: historical release entries describe past releases by design; #150 left them untouched and issue #152 explicitly excludes a CHANGELOG entry (owned by the release-prep commit). |
| `skills/`, `hosts/grok-bot/` (generated) | No impact: render `--write`/`--check` regenerated nothing (worktree stayed clean after render; budgets OK). |
| `tests/` | No impact: `tests/contract/test-issue-148-quota-packages.py:246` trailing whitespace stripped (the only trailing-whitespace line in that file); no test pins the corrected wording or the verifier bytes (verified by reading the consumers: behavioral roster/forbidden-pattern references only). |

## Issue-member walk (what satisfies each part)

1. `scripts/install-local.sh:76` nine→ten: satisfied — committed diff, one word.
2. `docs/codex-host.md:17` nine→ten: satisfied — committed diff, one word.
3. `docs/zcode-host.md:11` nine→ten: satisfied — committed diff, one word.
4. `docs/zcode-host.md:16` nine→ten: satisfied — committed diff, one word.
5. `tests/contract/test-issue-148-quota-packages.py:246` whitespace strip: satisfied — committed diff, one trailing space removed, nothing else touched in that file.
6. Remedy clause (render-skills.py --check and validate.sh exit 0 with receipted skips on this Studio): satisfied — `--check` PASS (budgets OK), `validate.sh` exit 0 (118 PASS, 0 FAIL, named bash<4 watchdog skips + 2 python>=3.10 prerequisite receipts in test-issue-51-runner-integration).
7. Disclosure: `scripts/kaola-grok-bot-verify.py:6` docstring nine→ten: Host independently verified and accepted, stays.

Follow-up items: none. No run-discovered defects; no duplicate probe with hits (repo-wide gate grep over scripts/, docs/, skills/, hosts/, README: zero user-facing hits; remaining matches are the out-of-scope render-skills.py code comments and historical CHANGELOG entries).
