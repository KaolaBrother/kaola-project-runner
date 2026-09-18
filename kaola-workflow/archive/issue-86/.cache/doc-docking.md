# Documentation docking — Issue #86

status: DOCKED
candidate: c0bcaf58a1ff37ddb55e1b19118125ffcc6febee (+ docs commit, see below)
changed public behavior: the shared Kaola-Delegator prompt's quota extraction
rule. Prompt-only. No CLI flag, script signature, JSON field, schema, state
file, or transport surface changed.

## Files checked

- `README.md` — FIXED in the candidate (mission 4). The A→B paragraph now
  states that quota travels in the units the user actually gave; an ungiven
  unit is carried as unspecified, does not block the start, is not unlimited,
  and is not a fourth question; an unclear unit is ambiguous, so ask. The
  Issue #74 sentence that `tests/contract/test-issue-74-kaola-delegator.py`
  pins verbatim is untouched (151 assertions PASS).
- `CHANGELOG.md` — FIXED at docking. Added the Issue #86 entry under
  `## Unreleased`, matching the per-issue `docs(iNN):` convention used by
  Issues #84 and #85. No release or tag was created.
- `AGENTS.md` — no impact. Its Layered entry line says the outer Agent hands
  off "authorized platforms/quota/priority"; it never enumerated the three
  quota units and remains true.
- `docs/architecture.md`, `docs/api.md`, `docs/conventions.md`,
  `docs/README.md`, `docs/grok-bot-host.md` — no impact. Verified by grep:
  they describe the Kaola-Delegator render topology (templates → `skills/`,
  the Grok Bot bridge bundle, budgets), not the Skill's quota extraction
  prose. No file states "three separate quota figures" or "stay three
  numbers".
- `docs/decisions/` — no impact. No decision record covers Delegator quota
  extraction; this run adds no new architectural decision (no schema, state
  file, quota engine, or transport gate).
- `skills/kaola-delegator/SKILL.md`,
  `skills/kaola-delegator/references/handoff.md` — generated surfaces, never
  hand-edited. Regenerated in the candidate via
  `./scripts/render-skills.py --write`; `--check` PASS with budgets OK
  (SKILL 4010/4096 B, handoff 8186/8192 B).
- Setup / install / environment / validation docs — no impact. The install
  command, `scripts/render-skills.py` flags, and `scripts/validate.sh` usage
  are unchanged; the only `validate.sh` edit registers the new suite in
  `python_suites_all` and `python_suites_b`.
- Examples — no impact. No example invokes the delegator quota fields.

## Verdict

DOCKED. Every documentation surface that states the changed behavior now
states it, and every surface left alone was checked and recorded as no-impact
with its reason.
