# Documentation Docking — Issue #212

Status: DOCKED

Checked against `AGENTS.md`'s documentation checklist for changed public behavior.

| Surface | Decision | Reason |
|---|---|---|
| `CHANGELOG.md` | **Updated** | Unreleased entry for Issue #212 added: guidance-only finalize safeguards, `Seats: restart not required` — the operator test `git diff OLD NEW -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms` is empty for this change. |
| `docs/architecture.md` | No change | Its pointer to `skills/kaola-project-runner/references/workflow-worktree.md` (worktree identity, `.kw/worktrees` not a security boundary) remains accurate; the new section is additive and changes none of the described facts. |
| `docs/conventions.md` | No change | The seat-restart and release conventions are satisfied by the CHANGELOG entry; no convention text changed and no release occurred. |
| `AGENTS.md` | No change | No command, installation step, validation policy, or project constraint changed; generated-surface handling already covers the rendered copy and manifests via `render-skills.py --write`/`--check`, which this run followed. |
| `README.md` | No change | No setup, usage, or entry-tier behavior changed; the four-tier entry descriptions are unaffected by an added orchestrator reference section. |
| `docs/api.md` | No change | No transport, receipt, adapter, or CLI surface changed; all changed files are prompt/reference guidance and generated hash manifests. |

Public behavior documented: the CHANGELOG entry names the four duties, the
affected run's scoped `.git/info/exclude` mitigation with byte-exact
restoration, the retire-by-conditions boundary, and the explicit non-goals
(no ownership table/scan/classifier/filter, no second acceptance engine, no
duplicate test run), plus the honest statement that Kaola-Workflow #1110
remains unresolved.
