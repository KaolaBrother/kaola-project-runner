<!-- kw:delivery project=bundle-54 issue=54 -->
# Issue #54 delivery and acceptance

Candidate `7c5cc2d1ad71d0665169c5a6e71225bc7d027d92` on `workflow/bundle-54` satisfies the installer-drift scope. This is an acceptance record before Workflow sink and release, not a release claim.

- Runtime `__pycache__`, `.pyc`, and `.pyo` no longer enter receipt tree digests or staged copies. Cache-only changes therefore do not look like a modified Skill.
- Ordinary reinstall of an exact receipt-owned copy with actual payload drift now reports `repair:`, atomically restores the generated source, preserves the previous bytes at the exact reported `.drift.*` sibling, and exits successfully. It does not add a runtime integrity gate or make installed files read-only.
- Foreign directories and links remain outside the receipt's ownership and are not overwritten. Modified-copy uninstall remains protective because removal is a separate destructive operation.
- Focused installer/migration tests, `./scripts/render-skills.py --check`, full `./scripts/validate.sh`, and `git diff --check` passed on the frozen candidate. An isolated real generated ZCode Skill install/edit/reinstall UAT demonstrated byte parity after repair and recoverable prior bytes; it did not touch live local installations.
- README, API documentation and CHANGELOG are docked. The already published v0.3.0 remains immutable. A separate v0.3.1 tag/Release and live local installation convergence follow after this Workflow transaction.
