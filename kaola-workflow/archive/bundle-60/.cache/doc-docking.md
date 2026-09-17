# Documentation docking — bundle-60 (Issue #60)

Changed public behavior checked: the generated claude-code worker Skill package no longer ships
`scripts/vendor/claude-code-acp/UPSTREAM.md` — the renderer's `VENDORED_BRIDGE_FILES` ship set
drops the provenance doc (package now carries only `dist/index.js` + `LICENSE`). The repo-root
provenance record `vendor/claude-code-acp/UPSTREAM.md` is unchanged and remains the source the
bridge provenance test reads. No runtime behavior, no manifest/schema, no user-visible surface
changed.

Checked against AGENTS.md's documentation checklist:

- `README.md` — NO IMPACT: no reference to the vendored file set or package internals; claude-code
  platform row unchanged.
- `docs/` (api, architecture, conventions, runner-v2 design, grok-bot-host, README, acp-watch) —
  NO IMPACT: none enumerate the vendored bridge file set.
- `AGENTS.md` — NO IMPACT: managed-region facts unaffected (vendor provenance record still exists).
- `CHANGELOG.md` — NO IMPACT: this is a packaging-internal fix (P3, not user-facing); it will be
  part of the 0.3.3 release notes as a maintenance item but needs no separate changelog entry
  beyond what the release covers.

DOCKED
