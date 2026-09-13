# Issue #26 error-surface repair

Worktree: `/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/issue-26`
Parent: `833fc86`

## Changes

- `scripts/kaola-acp.py` `command_view`: any socket error other than the frozen trio remaps to `holder-unreachable` (or `holder-lost` if pid is dead). `holder-closed` no longer appears on stdout.
- `scripts/kaola-tmux.sh`: `view` prints one `kaola-acp-view/1` object with `error.code=view-unsupported` and exits 1. No PTY fallback. `list` stays undispatched (`unknown command`).
- Watch tests: accept-then-close path; tmux `view-unsupported`; `--since 0` requires `cursor_gap`/`truncated` true; rotated jsonl 800 is the unique high-water mark; ContentItem union + `|null` fields pinned.

## Verification (worktree)

```
python3 tests/contract/test-acp-watch-contract.py -v   # 10 tests OK
python3 tests/contract/test-acp-contract.py            # 14 tests OK
python3 scripts/render-skills.py --write && --check    # PASS 6 Skills
./scripts/validate.sh                                  # VALIDATE_RC=0 (watch 10 OK)
git diff --stat templates/grok-golden                  # empty
```
