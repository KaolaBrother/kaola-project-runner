# Documentation docking — Issue #53

candidate: e60e87dd1d5c368ba6fdbe21c23e86b1ad353867 (workflow/issue-53, tree clean)
checked_at: 2026-09-16
checklist: AGENTS.md Documentation Map (README.md, CHANGELOG.md, docs/) plus the generated Skill
surfaces and the vendored fork's UPSTREAM.md.

## Changed public behavior

1. Session store removes its `.tmp` sibling when the rename into place fails (vendored bridge).
2. The per-session cancel flag is cleared when a turn starts (vendored bridge).
3. Holder notes agent child process groups (process tree + `KAOLA_ACP_CHILD_RECORD` spawn record),
   records `agent_child_pgids`/`agent_child_groups`, sweeps them on stop (`swept_child_pgids`);
   holder-lost `stop --force` sweeps recorded groups (`swept_pgids`); `ps` read under `LC_ALL=C`.
4. `permit` under the Claude bridge settles only the reported `tool_call` status.

## Checked files

| File | Result |
|---|---|
| README.md | FIXED in candidate (ACP bridge paragraph: permit semantics, `children.jsonl`, `swept_child_pgids`) |
| docs/api.md | FIXED in candidate (Transport selection: permit sentence; Stop section: child-group sweep, spawn record, identity pinning, holder-lost force path, `swept_pgids`) |
| CHANGELOG.md | FIXED in candidate (Unreleased entry for Issue #53; #56 and #52 entries preserved after the merge) |
| platforms/claude-code.yaml | FIXED in candidate (`acp_quirks` carries the permit fact) |
| skills/*/SKILL.md, skills/*/scripts, skills/*/references | REGENERATED (`render-skills.py --check` PASS at e60e87d, budgets OK; never hand-edited) |
| vendor/claude-code-acp/UPSTREAM.md | FIXED in candidate (modification list items 3/4, trust wording for the child record) |
| vendor/claude-code-acp/dist/DERIVATION.json | REGENERATED (`kaola-dist.py --check` OK rebuild=byte-identical at e60e87d) |
| docs/architecture.md | NO IMPACT (describes transport/relay layering, no residue-field or permit detail) |
| docs/conventions.md, docs/decisions/ | NO IMPACT (no convention or decision changed; the sweep and permit facts are behavior, not policy) |
| docs/runner-v2-dual-transport-design.md, docs/poc-acp-transport-2026-09-11.md, docs/acp-live-verification-2026-09-11.md | NO IMPACT (dated design/evidence records; not maintained as current-behavior references) |
| docs/grok-bot-host.md, hosts/grok-bot/ | NO IMPACT (Grok Bot host is out of scope; `kaola-grok-bot-verify.py` PASS in validate.sh) |
| AGENTS.md / CLAUDE.md | NO IMPACT (commands, constraints, and validation policy unchanged) |
| Examples | NO IMPACT (no example directory; README examples unchanged in meaning) |

## Verdict

DOCKED
