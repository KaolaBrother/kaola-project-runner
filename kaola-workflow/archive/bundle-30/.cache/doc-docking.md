# Doc Docking — bundle-30 (issue #30)

DOCKED

## Checked files

- `templates/SKILL.md.tmpl` — new "Ending, releasing, and resuming" section;
  rendered identically into all 7 generated `skills/*/SKILL.md`. DOCKED.
- `templates/references/acp.md.tmpl` — "Ending and resuming an ACP session":
  session/close when advertised, holder/agent exit + residue, end_turn ≠
  completion, close-name ≠ persistence, cancel/exit path for in-flight work. DOCKED.
- `templates/references/platform.md.tmpl` — `--continue`/`--resume` described as
  Runner options adapters translate to native syntax (supervisor-corrected);
  native session ID vs Runner session name; per-platform verified capability only.
  DOCKED.
- `templates/references/transport.md.tmpl` — PTY stop releases owned resources,
  reports actual exit, never deletes history. DOCKED.
- `README.md` — Chinese lifecycle paragraph carrying identical principles. DOCKED.
- `docs/api.md` — stop/resume semantics paragraph under Agent-directed transport
  results. DOCKED.
- `docs/conventions.md` — recommend-never-require convention sentence. DOCKED.
- `CHANGELOG.md` — Unreleased entry for issue #30. DOCKED.
- `docs/architecture.md` — no change needed; existing transport-integrity and
  agent-judgment text already consistent. NO-IMPACT.
- `AGENTS.md` — no change needed; contract text already states Agent owns
  completion judgments and Runner executes chosen operations. NO-IMPACT.

## Verification

- `./scripts/render-skills.py --check` PASS (7 Skills, no drift).
- `./scripts/validate.sh` PASS.
- `python3 tests/contract/test-generated-skills.py` PASS.
- `git diff templates/grok-golden/` — empty; frozen surface untouched.
- No runtime/tool code changed; no network smokes run (prose-only per issue
  acceptance criterion 5).
