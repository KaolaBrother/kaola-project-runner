# Documentation docking — issue-176

Candidate: workflow/issue-176 @ 10402a0 (rebased onto main 10b8379; test file
byte-identical to reviewed commit b482925). Change class: test-only fix plus
CHANGELOG entry. No script, template, adapter, platform manifest, or generated
surface changed, so no re-render was needed (`render-skills.py --check` green
inside validate.sh).

Checked against AGENTS.md's documentation map:

- `CHANGELOG.md` — DOCKED: the Unreleased entry for #176 is the user-visible
  record (root cause, fix, loop evidence, Seats line). The #178 entry from
  main is preserved alongside it after the rebase.
- `README.md` — no impact: no entry layer, usage, or overview behavior
  changed; the fix is internal to one contract suite's fixture hygiene.
- `docs/api.md` — no impact: the typed pre-mutation refusal receipt shape
  (`result: "refused"` with `reason`/`detail` and no `error`) is already the
  documented contract and is unchanged; the suite now simply checks it.
- `docs/` (architecture, conventions, decisions) — no impact: no runtime,
  protocol, workflow, or validation-policy change to document.
- `AGENTS.md` — no impact: validation policy and commands are unchanged.

DOCKED
