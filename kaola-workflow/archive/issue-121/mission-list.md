# #121 — a stale main Skill in a Host discovery root is refused at Host start, like #105 worker skew

1. item: Mechanism — render embeds the main Skill build record (per-file sha256 of the generated `kaola-project-runner` tree) as `scripts/main-skill-build.json` in every worker Skill; `kaola-acp.py` Host start compares every main Skill (SKILL.md frontmatter `name: kaola-project-runner`) in the platform's `HOST_SKILL_DISCOVERY_DIRS` against it after the #105 worker check; any difference → `main-skill-build-skew` pre-mutation refusal naming path + installed/expected build; detection only, no rewrite of user roots
   status: done
   dispatched: self, worktree .kw/worktrees/issue-121 (scripts/render-skills.py, scripts/kaola-acp.py)
   result: commit a75cb23 on workflow/issue-121 — scripts/render-skills.py main_skill_build_record → skills/*/scripts/main-skill-build.json; scripts/kaola-acp.py main_skill_alignment + main_skill_skew_refusal after the #105 gate
2. item: Contract tests in a temp root/shadow HOME — stale main Skill → Host start refused (detail names main Skill path, old and new build); aligned main Skill → start proceeds past the gate; #105 worker skew still refuses unchanged
   status: done
   dispatched: self, tests/contract/test-issue-119-host-entry.py (existing suite listed by validate.sh)
   result: commit a75cb23 — test_issue_121_main_skill_build_skew_refuses PASS (8 checks); test-issue-119-host-entry 10/10, 143 checks
3. item: Docs + gates — host-entry-matrix "same-named older copy wins" sentence, host-startup, api.md, zcode-host.md, CHANGELOG; render --write/--check; validate.sh rc=0 (foreground)
   status: done
   dispatched: self, worktree .kw/worktrees/issue-121; validate log kaola-workflow/issue-121/validate.log
   result: commit a75cb23 — render --write/--check PASS (budgets OK); validate.sh rc=0 (kaola-workflow/issue-121/validate.log); docs: host-entry-matrix, host-startup, docs/api.md, docs/zcode-host.md, CHANGELOG
