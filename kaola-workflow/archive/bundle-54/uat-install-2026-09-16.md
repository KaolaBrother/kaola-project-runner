# Issue #54 isolated install UAT (2026-09-16)

Candidate: `7c5cc2d1ad71d0665169c5a6e71225bc7d027d92` on `workflow/bundle-54`, clean. The published `v0.3.0` tag and all four live local Skill destinations were not modified by this UAT.

Temporary destination: `/tmp/kaola-installer-uat54.nlT19G/skills` (created for this test, then removed). The candidate installer copied the real generated `zcode-kaola-project-runner` Skill there with a valid receipt. A test-only `UAT_OWNED_COPY_DRIFT_54` line was added to that installed `SKILL.md`, not to the source. An ordinary second `install-local.sh --skills-dir ... --platform zcode --no-orchestrator --no-bin-links` exited 0 and printed `repair:` with the exact Skill path, a `.zcode-kaola-project-runner.drift.47182` previous-copy path and source-edit guidance. `diff -qr` between the generated Skill and repaired copy exited 0; the drift backup still contained the exact test line. Git in both the candidate worktree and main checkout remained clean apart from this run's untracked Workflow folder.

The temporary test destination, including its test-only backup, was removed after verification; no live installed copy, account, other worker, or published tag was touched. This proves install-time repair and preservation on a real generated Skill, not any new runtime execution restriction.

Offline evidence on the same commit: `test-installer-runtimes.sh` PASS, `test-installer-migration.sh` PASS, `render-skills.py --check` PASS, `validate.sh` exit 0 and `git diff --check` clean. Focused cache and source-cache cases were red on the baseline and green on the candidate. Foreign target refusal and modified-copy uninstall protection remain covered by the existing installer tests.
