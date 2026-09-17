# Issue #59: test-lifecycle-contract.py SKILL_IDS roster is stale: missing zcode and droid workers

Design of record: https://github.com/KaolaBrother/kaola-project-runner/issues/59 (filed from the #58 finalization run; iterative/passing coverage gap, P3).
Branch: `workflow/bundle-59` · Worktree: `.kw/worktrees/bundle-59` · Claim: acquired 2026-09-17 (main at dc3a379, synced).

- item: Add `zcode-kaola-project-runner` and `droid-kaola-project-runner` to the `SKILL_IDS` roster in `tests/contract/test-lifecycle-contract.py` so the lifecycle contract test covers all nine worker Skills, and pass full offline validation: `./scripts/render-skills.py --check` + `./scripts/validate.sh` exit 0. Test-only change; no product code, no docs impact, no changelog entry (not user-visible).
  status: done
  dispatched: self (orchestrator inline, worktree .kw/worktrees/bundle-59 on workflow/bundle-59), 2026-09-17; output = one test commit + full offline validation exit 0.
  result: Commit 8c284fd `test(lifecycle): cover zcode and droid in the SKILL_IDS roster` on workflow/bundle-59 (1 file, +2: zcode-kaola-project-runner + droid-kaola-project-runner added to SKILL_IDS in tests/contract/test-lifecycle-contract.py). Standalone run shows all nine workers pass the roster loop; the only RED is the pre-existing claude-code markdown inventory (vendored scripts/vendor/claude-code-acp/UPSTREAM.md not in EXPECTED_MARKDOWN) — out of scope for #59, filed as follow-up. Frozen candidate re-validation: full ./scripts/validate.sh exit 0 (VALIDATE_EXIT=0, log /tmp/bundle59-validate.log), receipt recorded (verdict pass, validated_candidate_hash a6eec2aa38584788ff54d41f21a150a2849f2755d81296a9116bedb0452aa191). Test-only change; no product code, no docs impact, no changelog entry.
