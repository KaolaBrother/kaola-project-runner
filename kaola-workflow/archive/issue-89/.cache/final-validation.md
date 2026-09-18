verdict: pass
validation_command: git diff --stat origin/main && test -z "$(git status --porcelain)" && ./scripts/render-skills.py --check
validated_candidate_hash: 9191c9dcbca0f78eb4f4146141e7a7cec410aa21cc58811f22baf5537a1ffcc9
