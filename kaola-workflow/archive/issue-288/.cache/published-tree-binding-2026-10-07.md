# #288 published-tree binding note — post-archive supplement (2026-10-07)

This note supplements the closed archive. The canonical
`.cache/final-validation.md` remains unchanged: `verdict: pass`, command
`/Users/ylmacstudio/.local/bin/bash ./scripts/validate.sh --suite test-issue-244-dispatch.py`,
and `validated_candidate_hash
5621fd54149b493c2952220bc7ec22aac952cd803ecee83d8ecf03aaf03d56b0`. No
validation record or hash was re-recorded or edited.

The implementation commit `4660b227` was merged with current `main`
`761b4509` into `workflow/issue-288` by merge commit
`d6392660783ab073f09e3339c74cbdbd3b73b05a` (parents `4660b227` and
`761b4509`; no rebase). The changelog keeps #288, #289, and #290 in issue
order, along with the preceding #287 entry.

At `d6392660`, the focused suite was rerun with the approved worktree-only
content-stage flip needed by the Grok pin guard. The renderer regenerated the
content-stage products, then the checks passed:

- `/Users/ylmacstudio/.local/bin/bash ./scripts/validate.sh --suite test-issue-244-dispatch.py`
  — exit 0, 80 tests passed, including the direct-seat preset test.
- `python3 ./scripts/render-skills.py --check` — exit 0.

The validation harness skipped its watchdog because the available Bash was
3.2.57; the suite and checks completed. The content-stage flip was restored
from `main`. `AGENTS.md`, `hosts/grok-bot/*`, and
`templates/grok-bot/accepted-revision.json` matched `main` before publication;
the published tree has no differences in those paths from `761b4509`. The
pre-push branch diff contained only the #288 implementation paths.

The merge sink published archive commit `ea78a9a39e5941e040ce26fe9f13abf70155648d`
(parent `d6392660`; tree `b8c1698322a1c3ade6d09067ff6b608e0a65b095`) to
`main` and closed issue #288. The first push attempt received a remote HTTP
500 without moving the remote tip; retrying the same resumable sink step
published successfully. The feature branch had been pushed fast-forward from
`4660b227` to `d6392660`; the sink then removed its remote and local branch.

The archived summary's candidate line describing a rebase onto `836bc41c` is
transaction-time text and does not describe the final integration. This note
records the actual merge lineage without rewriting that archived summary or
the canonical validation receipt.
