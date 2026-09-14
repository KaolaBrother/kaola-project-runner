# Issue #46 exact-candidate review

Candidate: `5cf5ab8ce520a005e22b12c310ff92fe1a49b544` on `workflow/issue-46`, based on current `main` at `bbccd96`.

Verdict: PASS. The observed failure was an installed main Skill symlink sharing the source file's inode. The candidate changes the installer default from `link` to `copy`, reuses existing owned-link migration and receipt protection, and adds a consumer-project boundary to the main orchestrator template and generated Skill. It adds no state machine, classifier, transport gate, or new refusal path. Explicit `--method link` remains for Project Runner development. Worker transport Skills and `templates/grok-golden/` are unchanged.

The review removed 50 lines of duplicate Issue #46 policy assertions from `test-issue-41-orchestrator.py`; the installer behavior remains covered by `test-installer-runtimes.sh`, and generated main Skill wording by `test-generated-skills.py`.

After that edit, `./scripts/render-skills.py --check && ./scripts/validate.sh && git diff --check main...HEAD && git diff --check` passed with exit 0. The validation ran on the candidate bytes before the review-only commit `5cf5ab8`; there is no subsequent product or test mutation. Live seven-platform tmux smoke was not rerun because start/send/read/stop transport did not change. Existing Codex/Devin source-linked installations still need default-copy migration after sink.

The optional Codex `--bin-links` helper executable symlinks are an existing interface and remain unchanged; they are outside the observed Skill-payload edit path. No new hard gate was added to address them.
