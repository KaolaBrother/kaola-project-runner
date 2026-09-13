# implement-verify — issue #27 local ACP `follow`

Worktree: `/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-27`
Branch: `workflow/bundle-27`
Did not commit.

## Commands and results

All commands run from the worktree.

```
python3 tests/contract/test-acp-follow-contract.py -v
```
exit 0 — Ran 11 tests in 6.339s — OK

```
python3 tests/contract/test-acp-watch-contract.py -q
```
exit 0 — Ran 10 tests in 4.209s — OK

```
python3 tests/contract/test-acp-contract.py -q
```
exit 0 — Ran 18 tests in 21.658s — OK

```
./scripts/render-skills.py --write
```
exit 0 — `render-skills: WROTE (6 Skills)`

```
./scripts/render-skills.py --check
```
exit 0 — `render-skills: PASS (6 Skills)`

```
./scripts/validate.sh
```
exit 0 — render check PASS; six Skills valid; issue-9, direct-transport, devin-regressions, acp, acp-watch (10), acp-follow (11), runner-v2, generated Skill acceptance, issue-24 all OK

```
git diff --stat templates/grok-golden
```
exit 0 — empty (no output)

```
git diff --check
```
exit 0 — no whitespace errors

## Not run

- Live tmux smoke per platform (start/observe/send/capture/stop)
- Live CLI UAT against real agent binaries
- install-local.sh

## Leftover

None. Follow contract 11/11 green. #26 watch and ACP contracts green. `templates/grok-golden/` untouched.
