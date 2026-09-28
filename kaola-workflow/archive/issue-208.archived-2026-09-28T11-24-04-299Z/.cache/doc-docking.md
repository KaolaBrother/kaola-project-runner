# Documentation Docking — issue-208 (second finalize, reopened QA finding)

Candidate: `52bf5abf` on `workflow/issue-208` (base `68e6e2ef`).
Scope: one bounded QA finding — README.md carried a stale seat-stop sentence contradicting the
lifecycle-once semantics this issue already landed.

## Changed paths

- `README.md` — 2 insertions, 1 deletion.

## Checked files

| File | Impact | Reason |
|---|---|---|
| `README.md` | FIXED | The only changed surface. The Elite-preset authorization bullet now states acceptance-before-finalize, the accepted seat keeping only its owned finalize/cleanup duties, and exact-stop once it owns none or is abandoned. This mirrors `templates/orchestrator/SKILL.md.tmpl` step 5 (canonical lifecycle-once wording). |
| `templates/orchestrator/SKILL.md.tmpl` | NO IMPACT | Canonical lifecycle source already correct; not edited by this run. The README was brought to it, not the reverse. |
| `templates/orchestrator/references/host-startup.md.tmpl` | NO IMPACT | Its `delivery is accepted or abandoned → stop, prove gone` row is a different, correct meaning (a dead/errored seat's stop condition), not the stop-at-acceptance contradiction. Verified by grep; left untouched. |
| `CHANGELOG.md` | NO IMPACT | No user-visible behavior, CLI, transport, or API change; a single stale maintainer-facing wording correction inside an existing bullet. No release in this run. |
| `docs/*` | NO IMPACT | No architecture/API/convention content changed. `docs/harness-acp-compat-2026-09-25.md` and `-26.md` are protected and were not read, staged, or copied. |
| Generated surfaces (`skills/`, `hosts/grok-bot/`) | NO IMPACT | README is not a render source. `render-skills.py --write` produced no byte change; `--check` PASS. |

## Verification

- No other README instance of the same-meaning contradiction remains (grep for `stop each seat`,
  `once its delivery is accepted`, `seat once`, and equivalents → no hit).
- Existing README pin in `tests/contract/test-issue-118-seat-cap.py`
  (`authorized count … hard cap on live worker processes … stop-before-start`) re-verified against
  the new text: still matches. No stale pin; no test edited.
- `./scripts/render-skills.py --write` → WROTE, budgets OK.
- `./scripts/render-skills.py --check` → PASS, budgets OK.
- `./scripts/validate.sh` → exit 0, 49 suites, zero failures.

DOCKED
